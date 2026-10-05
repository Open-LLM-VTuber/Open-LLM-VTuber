const CHARACTER_CONFIG = "aster.yaml";
const CHARACTER_NAME = "Aster Vale";

const statusText = document.querySelector("#connection-status");
const statusDot = document.querySelector("#status-dot");
const composerHint = document.querySelector("#composer-hint");
const messageForm = document.querySelector("#message-form");
const messageInput = document.querySelector("#message-input");
const messageList = document.querySelector("#message-list");
const sendButton = document.querySelector("#send-button");
const voiceToggle = document.querySelector("#voice-toggle");
const voiceLabel = document.querySelector("#voice-label");

let socket;
let connected = false;
let characterReady = false;
let waitingForResponse = false;
let configSwitchRequested = false;
let assistantMessage = null;
let voiceEnabled = true;
let audioPlaying = false;
let activeAudio = null;
let playbackCompletionPending = false;
const audioQueue = [];

function setStatus(text, state = "connecting") {
  statusText.textContent = text;
  statusDot.dataset.state = state;
}

function setHint(text, state = "normal") {
  composerHint.textContent = text;
  composerHint.dataset.state = state;
}

function updateControls() {
  const canSend = connected && characterReady && !waitingForResponse;
  messageInput.disabled = !canSend;
  sendButton.disabled = !canSend;
  voiceToggle.disabled = !connected || !characterReady;
}

function updateVoiceToggle() {
  voiceToggle.setAttribute("aria-pressed", String(voiceEnabled));
  voiceLabel.textContent = voiceEnabled ? "Voice on" : "Voice off";
}

function addMessage(role, text = "") {
  const article = document.createElement("article");
  article.className = `message ${role}-message`;

  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");

    const image = document.createElement("img");
    image.src = "/character-call/assets/aster.svg";
    image.alt = "";
    avatar.append(image);
    article.append(avatar);
  }

  const content = document.createElement("div");
  content.className = "message-content";

  const author = document.createElement("span");
  author.className = "message-author";
  author.textContent = role === "assistant" ? CHARACTER_NAME : "You";

  const messageText = document.createElement("p");
  messageText.className = "message-text";
  messageText.textContent = text;

  content.append(author, messageText);
  article.append(content);
  messageList.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return messageText;
}

function showThinking() {
  if (!assistantMessage) {
    assistantMessage = addMessage("assistant", "Thinking…");
  }
}

function appendAssistantText(text) {
  if (!text) {
    return;
  }

  showThinking();
  const currentText = assistantMessage.textContent;
  if (currentText === "Thinking…" || currentText === "Thinking...") {
    assistantMessage.textContent = text;
  } else {
    assistantMessage.textContent = `${currentText} ${text}`;
  }
  messageList.lastElementChild?.scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });
}

function sendSocketMessage(message) {
  if (socket?.readyState !== WebSocket.OPEN) {
    throw new Error("The connection to the server is not open.");
  }
  socket.send(JSON.stringify(message));
}

function switchToAster(configs) {
  if (configSwitchRequested) {
    return;
  }

  const configExists = configs.some((config) => config.filename === CHARACTER_CONFIG);
  if (!configExists) {
    setStatus(`Character config ${CHARACTER_CONFIG} was not found.`, "error");
    setHint("Restart the server after adding the Aster character config.", "error");
    return;
  }

  configSwitchRequested = true;
  setStatus("Preparing Aster…");
  try {
    sendSocketMessage({ type: "switch-config", file: CHARACTER_CONFIG });
  } catch (error) {
    setStatus(error.message, "error");
    setHint("Could not select the character configuration.", "error");
  }
}

function queueAudio(payload) {
  const displayText = payload.display_text?.text;
  if (typeof displayText === "string") {
    appendAssistantText(displayText);
  }

  if (voiceEnabled && typeof payload.audio === "string" && payload.audio.length) {
    audioQueue.push(payload.audio);
    void playNextAudio();
  } else {
    maybeCompletePlayback();
  }
}

async function playNextAudio() {
  if (audioPlaying || !voiceEnabled) {
    maybeCompletePlayback();
    return;
  }

  const encodedAudio = audioQueue[0];
  if (!encodedAudio) {
    maybeCompletePlayback();
    return;
  }

  const player = new Audio(`data:audio/wav;base64,${encodedAudio}`);
  activeAudio = player;
  audioPlaying = true;
  let playbackSettled = false;

  player.onended = () => {
    if (playbackSettled) {
      return;
    }
    playbackSettled = true;
    audioQueue.shift();
    activeAudio = null;
    audioPlaying = false;
    void playNextAudio();
  };

  player.onerror = () => {
    if (playbackSettled) {
      return;
    }
    playbackSettled = true;
    audioQueue.shift();
    activeAudio = null;
    audioPlaying = false;
    setHint("A voice response could not be played. Text replies will still appear.", "error");
    void playNextAudio();
  };

  try {
    await player.play();
  } catch (error) {
    if (activeAudio === player) {
      activeAudio = null;
      audioPlaying = false;
    }

    if (error.name === "NotAllowedError") {
      if (!playbackSettled) {
        voiceEnabled = false;
        updateVoiceToggle();
        setHint("Audio is blocked. Tap Voice off to enable spoken replies.", "normal");
        maybeCompletePlayback();
      }
      return;
    }

    if (!playbackSettled) {
      playbackSettled = true;
      audioQueue.shift();
      setHint(`Voice playback failed: ${error.message}`, "error");
      void playNextAudio();
    }
  }
}

function sendPlaybackComplete() {
  playbackCompletionPending = false;
  try {
    sendSocketMessage({ type: "frontend-playback-complete" });
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function maybeCompletePlayback() {
  if (
    playbackCompletionPending &&
    (!voiceEnabled || (!audioPlaying && audioQueue.length === 0))
  ) {
    sendPlaybackComplete();
  }
}

function handleMessage(message) {
  switch (message.type) {
    case "config-files":
      switchToAster(message.configs ?? []);
      break;
    case "config-switched":
      characterReady = true;
      connected = true;
      waitingForResponse = false;
      setStatus("Aster is here", "ready");
      setHint("Messages are sent to your configured Open-LLM-VTuber server.");
      updateControls();
      messageInput.focus();
      break;
    case "full-text":
      if (message.text === "Thinking…" || message.text === "Thinking...") {
        showThinking();
      }
      break;
    case "audio":
      queueAudio(message);
      break;
    case "backend-synth-complete":
      playbackCompletionPending = true;
      maybeCompletePlayback();
      break;
    case "force-new-message":
      assistantMessage = null;
      waitingForResponse = false;
      updateControls();
      break;
    case "control":
      if (message.text === "conversation-chain-start") {
        setStatus("Aster is gathering a thought…", "ready");
      } else if (message.text === "conversation-chain-end") {
        waitingForResponse = false;
        setStatus("Aster is here", "ready");
        updateControls();
      }
      break;
    case "error":
      setStatus(message.message || "The server reported an error.", "error");
      setHint(message.message || "The server could not complete that request.", "error");
      if (!characterReady) {
        configSwitchRequested = false;
        updateControls();
      } else {
        waitingForResponse = false;
        updateControls();
      }
      break;
    default:
      break;
  }
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${window.location.host}/client-ws`);

  socket.addEventListener("open", () => {
    connected = true;
    setStatus("Finding Aster’s profile…");
    updateControls();
    try {
      sendSocketMessage({ type: "fetch-configs" });
    } catch (error) {
      setStatus(error.message, "error");
    }
  });

  socket.addEventListener("message", (event) => {
    try {
      handleMessage(JSON.parse(event.data));
    } catch (error) {
      setHint(`Could not read a server message: ${error.message}`, "error");
    }
  });

  socket.addEventListener("error", () => {
    setStatus("Could not connect to the server.", "error");
    setHint("Check that Open-LLM-VTuber is running, then reload this page.", "error");
  });

  socket.addEventListener("close", () => {
    connected = false;
    characterReady = false;
    waitingForResponse = false;
    setStatus("Disconnected", "error");
    setHint("The server connection closed. Reload to reconnect.", "error");
    updateControls();
  });
}

messageForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text || !connected || !characterReady || waitingForResponse) {
    return;
  }

  try {
    sendSocketMessage({ type: "text-input", text });
    addMessage("user", text);
    assistantMessage = null;
    waitingForResponse = true;
    messageInput.value = "";
    messageInput.style.height = "";
    setStatus("Aster is gathering a thought…", "ready");
    updateControls();
  } catch (error) {
    setStatus(error.message, "error");
    setHint("Your message was not sent.", "error");
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 140)}px`;
});

voiceToggle.addEventListener("click", () => {
  voiceEnabled = !voiceEnabled;
  updateVoiceToggle();

  if (voiceEnabled) {
    setHint("Spoken replies are on.");
    void playNextAudio();
  } else {
    activeAudio?.pause();
    activeAudio = null;
    audioPlaying = false;
    audioQueue.length = 0;
    setHint("Spoken replies are off; text replies will still appear.");
    maybeCompletePlayback();
  }
});

connect();
