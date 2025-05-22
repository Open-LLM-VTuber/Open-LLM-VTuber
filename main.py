import os
import sys
import re
import random
import shutil
import atexit
import threading
import queue
import uuid
from typing import Callable, Iterator, Optional
import datetime
from loguru import logger
import numpy as np
import yaml
import chardet

import __init__
from asr.asr_factory import ASRFactory
from asr.asr_interface import ASRInterface
from live2d_model import Live2dModel
from llm.llm_factory import LLMFactory
from llm.llm_interface import LLMInterface
from prompts import prompt_loader
from tts.tts_factory import TTSFactory
from tts.tts_interface import TTSInterface
from translate.translate_interface import TranslateInterface
from translate.translate_factory import TranslateFactory
from utils.audio_preprocessor import audio_filter
from utils.audio_utils import save_audio_to_wav # For saving user input audio


class OpenLLMVTuberMain:
    """
    The main class for the OpenLLM VTuber.
    It initializes the Live2D controller, ASR, TTS, and LLM based on the provided configuration.
    Run `conversation_chain` to start one conversation (user_input -> llm -> speak).

    Attributes:
    - config (dict): The configuration dictionary.
    - llm (LLMInterface): The LLM instance.
    - asr (ASRInterface): The ASR instance.
    - tts (TTSInterface): The TTS instance.
    """

    EXEC_FLAG_CHECK_TIMEOUT = 8  # seconds

    def __init__(
        self,
        configs: dict,
        custom_asr: ASRInterface | None = None,
        custom_tts: TTSInterface | None = None,
    ) -> None:
        logger.info(f"t41372/Open-LLM-VTuber, version {__init__.__version__}")

        self.config: dict = configs
        self.verbose = self.config.get("VERBOSE", False)
        self.live2d: Live2dModel | None = self.init_live2d()
        self._continue_exec_flag = threading.Event()
        self._continue_exec_flag.set()  # Set the flag to continue execution
        self.session_id: str = str(uuid.uuid4().hex)
        self.heard_sentence: str = ""

        # Init ASR if voice input is on.
        self.asr: ASRInterface | None
        if self.config.get("VOICE_INPUT_ON", False):
            # if custom_asr is provided, don't init asr and use it instead.
            if custom_asr is None:
                self.asr = self.init_asr()
            else:
                print("Using custom ASR")
                self.asr = custom_asr
        else:
            self.asr = None

        # Init TTS if TTS is on.
        self.tts: TTSInterface
        if self.config.get("TTS_ON", False):
            # if custom_tts is provided, don't init tts and use it instead.
            if custom_tts is None:
                self.tts = self.init_tts()
            else:
                print("Using custom TTS")
                self.tts = custom_tts
        else:
            self.tts = None

        # Init Translator if enabled
        self.translator: TranslateInterface | None
        if self.config.get("TRANSLATE_AUDIO", False):
            try:
                translate_provider = self.config.get("TRANSLATE_PROVIDER", "DeepLX")
                self.translator = TranslateFactory.get_translator(
                    translate_provider=translate_provider,
                    **self.config.get(translate_provider, {}),
                )
            except Exception as e:
                print(f"Error initializing Translator: {e}")
                print("Proceed without Translator.")
                self.translator = None
        else:
            self.translator = None

        self.llm: LLMInterface = self.init_llm()
        self._init_chat_history_dir()


    def _init_chat_history_dir(self):
        """Initializes the chat history directory and session directory if recording is enabled."""
        if self.config.get("SAVE_CHAT_HISTORY", False) and \
           self.config.get("RECORDING", {}).get("RECORD_CONVERSATIONS", False):
            chat_history_dir = self.config.get("CHAT_HISTORY_DIR", "./chat_history/")
            self.session_log_dir = os.path.join(chat_history_dir, self.session_id)
            if not os.path.exists(self.session_log_dir):
                try:
                    os.makedirs(self.session_log_dir)
                    logger.info(f"Created session log directory: {self.session_log_dir}")
                except OSError as e:
                    logger.error(f"Error creating session log directory {self.session_log_dir}: {e}")
                    # Disable further recording attempts for this session if dir creation fails
                    self.config["RECORDING"]["RECORD_CONVERSATIONS"] = False 
        else:
            self.session_log_dir = None

    # Initialization methods

    def init_live2d(self) -> Live2dModel | None:
        if not self.config.get("LIVE2D", False):
            return None
        try:
            live2d_model_name = self.config.get("LIVE2D_MODEL")
            live2d_controller = Live2dModel(live2d_model_name)
        except Exception as e:
            print(f"Error initializing Live2D: {e}")
            print("Proceed without Live2D.")
            return None
        return live2d_controller

    def init_llm(self) -> LLMInterface:
        llm_provider = self.config.get("LLM_PROVIDER")
        llm_config = self.config.get(llm_provider, {})
        system_prompt = self.get_system_prompt()

        llm = LLMFactory.create_llm(
            llm_provider=llm_provider, SYSTEM_PROMPT=system_prompt, **llm_config
        )
        return llm

    def init_asr(self) -> ASRInterface:
        asr_model = self.config.get("ASR_MODEL")
        asr_config = self.config.get(asr_model, {})
        asr = ASRFactory.get_asr_system(asr_model, **asr_config)
        return asr

    def init_tts(self) -> TTSInterface:
        tts_model = self.config.get("TTS_MODEL", "pyttsx3TTS")
        tts_config = self.config.get(tts_model, {})
        return TTSFactory.get_tts_engine(tts_model, **tts_config)

    def set_audio_output_func(
        self, audio_output_func: Callable[[Optional[str], Optional[str]], None]
    ) -> None:
        """
        Set the audio output function to be used for playing audio files.
        The function should accept two arguments: sentence (str) and filepath (str).

        sentence: str | None
        - The sentence to be displayed on the frontend.
        - If None, empty sentence will be displayed.

        filepath: str | None
        - The path to the audio file to be played.
        - If None, no audio will be played.

        Here is an example of the function:
        ~~~python
        def _play_audio_file(sentence: str | None, filepath: str | None) -> None:
            if filepath is None:
                print("No audio to be streamed. Response is empty.")
                return

            if sentence is None:
                sentence = ""
            print(f">> Playing {filepath}...")
            playsound(filepath)
        ~~~
        """

        self._play_audio_file = audio_output_func

        # def _play_audio_file(self, sentence: str, filepath: str | None) -> None:

    def get_system_prompt(self) -> str:
        """
        Construct and return the system prompt based on the configuration file.
        """
        if self.config.get("PERSONA_CHOICE"):
            system_prompt = prompt_loader.load_persona(
                self.config.get("PERSONA_CHOICE")
            )
        else:
            system_prompt = self.config.get("DEFAULT_PERSONA_PROMPT_IN_YAML")

        if self.live2d is not None:
            system_prompt += prompt_loader.load_util(
                self.config.get("LIVE2D_Expression_Prompt")
            ).replace("[<insert_emomap_keys>]", self.live2d.emo_str)

        if self.verbose:
            print("\n === System Prompt ===")
            print(system_prompt)

        return system_prompt

    # Main conversation methods

    def conversation_chain(self, user_input: str | np.ndarray | None = None) -> str:
        """
        One iteration of the main conversation.
        1. Get user input (text or audio) if not provided as an argument
        2. Call the LLM with the user input
        3. Speak (or not)

        Parameters:
        - user_input (str, numpy array, or None): The user input to be used in the conversation. If it's string, it will be considered as user input. If it's a numpy array, it will be transcribed. If it's None, we'll request input from the user.

        Returns:
        - str: The full response from the LLM
        """

        if not self._continue_exec_flag.wait(
            timeout=self.EXEC_FLAG_CHECK_TIMEOUT
        ):  # Wait for the flag to be set
            print(
                ">> Execution flag not set. In interruption state for too long. Resetting the flag and exiting the conversation chain."
            )
            self._continue_exec_flag.set()
            raise InterruptedError(
                "Conversation chain interrupted. Wait flag timeout reached."
            )

        # Generate a random number between 0 and 3
        color_code = random.randint(0, 3)
        c = [None] * 4
        # Define the color codes for red, blue, green, and white
        c[0] = "\033[91m"
        c[1] = "\033[94m"
        c[2] = "\033[92m"
        c[3] = "\033[0m"

        # Apply the color to the console output
        print(f"{c[color_code]}New Conversation Chain started!")

        # if user_input is not string, make it string
        if user_input is None:
            user_input = self.get_user_input()
        elif isinstance(user_input, np.ndarray):
            print("transcribing...")
            user_input = self.asr.transcribe_np(user_input)

        if user_input.strip().lower() == self.config.get("EXIT_PHRASE", "exit").lower():
            print("Exiting...")
            exit()

        print(f"User input: {user_input}")

        # Log user input to transcript
        self._log_to_transcript(f"User: {user_input}")

        chat_completion: Iterator[str] = self.llm.chat_iter(user_input)

        if not self.config.get("TTS_ON", False):
            full_response = ""
            for char in chat_completion:
                if not self._continue_exec_flag.is_set():
                    self._interrupt_post_processing()
                    print("\nInterrupted!")
                    return None
                full_response += char
                print(char, end="")
            return full_response

        full_response = self.speak(chat_completion)
        if self.verbose:
            print(f"\nComplete response: [\n{full_response}\n]")

        # Log AI response to transcript
        if full_response: # full_response can be None if interrupted
            self._log_to_transcript(f"AI: {full_response}")
            self._log_to_transcript("---") # Separator

        print(f"{c[color_code]}Conversation completed.")
        return full_response

    def get_user_input(self) -> str:
        """
        Get user input using the method specified in the configuration file.
        It can be from the console, local microphone, or the browser microphone.

        Returns:
        - str: The user input
        """
        # for live2d with browser, their input are now injected by the server class
        # and they no longer use this method
        if self.config.get("VOICE_INPUT_ON", False):
            # get audio from the local microphone
            print("Listening from the microphone...")
            if self.config.get("RECORDING", {}).get("RECORD_CONVERSATIONS", False) and self.session_log_dir and self.asr:
                # User audio recording is enabled
                audio_format = self.config.get("RECORDING", {}).get("AUDIO_RECORDING_FORMAT", "wav")
                return self.asr.transcribe_with_local_vad(
                    audio_save_callback=save_audio_to_wav, # The actual function from audio_utils
                    audio_save_format=audio_format,
                    session_log_dir=self.session_log_dir
                )
            else:
                # Recording not enabled or session_log_dir not set, proceed without saving
                return self.asr.transcribe_with_local_vad()
        else:
            return input("\n>> ")

    def speak(self, chat_completion: Iterator[str]) -> str:
        """
        Speak the chat completion using the TTS engine.

        Parameters:
        - chat_completion (Iterator[str]): The chat completion to speak

        Returns:
        - str: The full response from the LLM
        """
        full_response = ""
        if self.config.get("SAY_SENTENCE_SEPARATELY", True):
            full_response = self.speak_by_sentence_chain(chat_completion)
        else:  # say the full response at once? how stupid
            full_response = ""
            for char in chat_completion:
                if not self._continue_exec_flag.is_set():
                    print("\nInterrupted!")
                    self._interrupt_post_processing()
                    return None
                print(char, end="")
                full_response += char
            print("\n")
            filename = self._generate_audio_file(full_response, "temp")

            if self._continue_exec_flag.is_set():
                self._play_audio_file(
                    sentence=full_response,
                    filepath=filename,
                )
            else:
                self._interrupt_post_processing()

        return full_response

    def _generate_audio_file(self, sentence: str, file_name_no_ext: str) -> str | None:
        """
        Generate an audio file from the given sentence using the TTS engine.

        Parameters:
        - sentence (str): The sentence to generate audio from
        - file_name_no_ext (str): The name of the audio file without the extension

        Returns:
        - str or None: The path to the generated audio file or None if the sentence is empty
        """
        if self.verbose:
            print(f">> generating TTS audio for: '{sentence[:30]}...'")

        if not self.tts:
            logger.warning("TTS engine not available, cannot generate audio.")
            return None

        original_sentence_for_display = sentence # Keep original for display if live2d removes keywords

        if self.live2d:
            sentence = self.live2d.remove_emotion_keywords(sentence)

        if sentence.strip() == "":
            logger.info("Sentence is empty after potential keyword removal, no audio to generate.")
            return None
        
        # Let TTS generate audio to its usual cache location first
        # The file_name_no_ext is often a UUID or "temp" for cache management
        original_filepath = self.tts.generate_audio(sentence, file_name_no_ext=file_name_no_ext)

        if not original_filepath or not os.path.exists(original_filepath):
            logger.error(f"TTS engine failed to generate audio file or file not found at {original_filepath}")
            return None

        # If recording is enabled, copy the generated audio to the session directory
        if self.config.get("RECORDING", {}).get("RECORD_CONVERSATIONS", False) and \
           self.config.get("TTS_ON", False) and self.session_log_dir:
            try:
                audio_format = self.config.get("RECORDING", {}).get("AUDIO_RECORDING_FORMAT", "wav")
                # Ensure the format from TTS matches the recording format, or handle conversion (future)
                # For now, assume they match or the TTS output is desired as is.
                
                # Extract the original extension (e.g., .wav, .mp3) from original_filepath
                _, original_ext = os.path.splitext(original_filepath)
                if not original_ext: # Default if something is wrong
                    original_ext = f".{audio_format}"

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                # Use original_ext for the recorded file to match what TTS produced
                session_audio_filename = f"ai_tts_output_{timestamp}{original_ext}"
                session_audio_filepath = os.path.join(self.session_log_dir, session_audio_filename)
                
                shutil.copy(original_filepath, session_audio_filepath)
                logger.info(f"TTS output audio saved to session directory: {session_audio_filepath}")
            except Exception as e:
                logger.error(f"Error copying TTS audio to session directory: {e}")
        
        # Return the path to the original cached audio file for playback and subsequent removal by _play_audio_file
        return original_filepath

    def _play_audio_file(self, sentence: str | None, filepath: str | None) -> None:
        """
        Play the audio file either locally or remotely using the Live2D controller if available.

        Parameters:
        - sentence (str): The sentence to display
        - filepath (str): The path to the audio file. If None, no audio will be streamed.
        """

        if filepath is None:
            print("No audio to be streamed. Response is empty.")
            return

        if sentence is None:
            sentence = ""

        try:
            if self.verbose:
                print(f">> Playing {filepath}...")
            self.tts.play_audio_file_local(filepath)

            self.tts.remove_file(filepath, verbose=self.verbose)
        except ValueError as e:
            if str(e) == "Audio is empty or all zero.":
                print("No audio to be streamed. Response is empty.")
            else:
                raise e
        except Exception as e:
            print(f"Error playing the audio file {filepath}: {e}")

    def speak_by_sentence_chain(self, chat_completion: Iterator[str]) -> str:
        """
        Generate and play the chat completion sentences one by one using the TTS engine.
        Now properly handles interrupts in a multi-threaded environment using the existing _continue_exec_flag.
        """
        task_queue = queue.Queue()
        full_response = [""]  # Use a list to store the full response
        interrupted_error_event = threading.Event()

        def producer_worker():
            try:
                index = 0
                sentence_buffer = ""

                for char in chat_completion:
                    if not self._continue_exec_flag.is_set():
                        raise InterruptedError("Producer interrupted")

                    if char:
                        print(char, end="", flush=True)
                        sentence_buffer += char
                        full_response[0] += char
                        if self.is_complete_sentence(sentence_buffer):
                            if self.verbose:
                                print("\n")
                            if not self._continue_exec_flag.is_set():
                                raise InterruptedError("Producer interrupted")
                            tts_target_sentence = sentence_buffer

                            tts_target_sentence = audio_filter(
                                tts_target_sentence,
                                translator=(
                                    self.translator
                                    if self.config.get("TRANSLATE_AUDIO", False)
                                    else None
                                ),
                                remove_special_char=self.config.get(
                                    "REMOVE_SPECIAL_CHAR", True
                                ),
                            )

                            audio_filepath = self._generate_audio_file(
                                tts_target_sentence, file_name_no_ext=uuid.uuid4()
                            )

                            if not self._continue_exec_flag.is_set():
                                raise InterruptedError("Producer interrupted")
                            audio_info = {
                                "sentence": sentence_buffer,
                                "audio_filepath": audio_filepath,
                            }
                            task_queue.put(audio_info)
                            index += 1
                            sentence_buffer = ""

                # Handle any remaining text in the buffer
                if sentence_buffer:
                    if not self._continue_exec_flag.is_set():
                        raise InterruptedError("Producer interrupted")
                    print("\n")
                    audio_filepath = self._generate_audio_file(
                        sentence_buffer, file_name_no_ext=uuid.uuid4()
                    )
                    audio_info = {
                        "sentence": sentence_buffer,
                        "audio_filepath": audio_filepath,
                    }
                    task_queue.put(audio_info)

            except InterruptedError:
                print("\nProducer interrupted")
                interrupted_error_event.set()
                return  # Exit the function
            except Exception as e:
                print(
                    f"Producer error: Error generating audio for sentence: '{sentence_buffer}'.\n{e}",
                    "Producer stopped\n",
                )
                return
            finally:
                task_queue.put(None)  # Signal end of production

        def consumer_worker():
            self.heard_sentence = ""

            while True:

                try:
                    if not self._continue_exec_flag.is_set():
                        raise InterruptedError("😱Consumer interrupted")

                    audio_info = task_queue.get(
                        timeout=0.1
                    )  # Short timeout to check for interrupts
                    if audio_info is None:
                        break  # End of production
                    if audio_info:
                        current_sentence = audio_info["sentence"]
                        self.heard_sentence += current_sentence
                        self._play_audio_file(
                            sentence=current_sentence, # Use current sentence for display
                            filepath=audio_info["audio_filepath"],
                            # Pass full_response_for_recording if needed, or handle in _generate_audio_file
                        )
                    task_queue.task_done()
                except queue.Empty:
                    continue  # No item available, continue checking for interrupts
                except InterruptedError as e:
                    print(f"\n{str(e)}, stopping worker threads")
                    interrupted_error_event.set()
                    return  # Exit the function
                except Exception as e:
                    print(
                        f"Consumer error: Error playing sentence '{audio_info['sentence']}'.\n {e}"
                    )
                    continue

        producer_thread = threading.Thread(target=producer_worker)
        consumer_thread = threading.Thread(target=consumer_worker)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join()

        if interrupted_error_event.is_set():
            self._interrupt_post_processing()
            raise InterruptedError(
                "Conversation chain interrupted: consumer model interrupted"
            )

        print("\n\n --- Audio generation and playback completed ---")
        return full_response[0]

    def interrupt(self, heard_sentence: str = "") -> None:
        """Set the interrupt flag to stop the conversation chain.
        Preferably provide the sentences that were already shown or heard by the user before the interrupt so that the LLM can handle the memory properly.

        Parameters:
        - heard_sentence (str): The sentence that was already shown or heard by the user before the interrupt.
            (because apparently the user won't know the rest of the response.)
        """
        self._continue_exec_flag.clear()
        # Log interruption to transcript
        interruption_message = f"Interrupted by user. Last heard/displayed sentence: {heard_sentence}"
        logger.info(interruption_message)
        self._log_to_transcript(f"SYSTEM: {interruption_message}")
        self.llm.handle_interrupt(heard_sentence)

    def _interrupt_post_processing(self) -> None:
        """Perform post-processing tasks (like resetting the continue flag to allow next conversation chain to start) after an interrupt."""
        self._log_to_transcript("SYSTEM: Resuming normal operation after interruption.")
        self._continue_exec_flag.set()  # Reset the interrupt flag

    def _check_interrupt(self):
        """Check if we are in an interrupt state and raise an exception if we are."""
        if not self._continue_exec_flag.is_set():
            # Log check interrupt failure
            # self._log_to_transcript("SYSTEM: Interruption check failed, raising InterruptedError.")
            raise InterruptedError("Conversation chain interrupted: checked")

    def _log_to_transcript(self, message: str):
        """Appends a message to the transcript.txt file in the session log directory."""
        if self.config.get("SAVE_CHAT_HISTORY", False) and \
           self.config.get("RECORDING", {}).get("RECORD_CONVERSATIONS", False) and \
           self.session_log_dir:
            try:
                transcript_path = os.path.join(self.session_log_dir, "transcript.txt")
                # Get current timestamp
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(transcript_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {message}\n")
            except Exception as e:
                logger.error(f"Failed to write to transcript file {transcript_path}: {e}")

    def is_complete_sentence(self, text: str):
        """
        Check if the text is a complete sentence.
        text: str
            the text to check
        """

        white_list = [
            "...",
            "Dr.",
            "Mr.",
            "Ms.",
            "Mrs.",
            "Jr.",
            "Sr.",
            "St.",
            "Ave.",
            "Rd.",
            "Blvd.",
            "Dept.",
            "Univ.",
            "Prof.",
            "Ph.D.",
            "M.D.",
            "U.S.",
            "U.K.",
            "U.N.",
            "E.U.",
            "U.S.A.",
            "U.K.",
            "U.S.S.R.",
            "U.A.E.",
        ]

        for item in white_list:
            if text.strip().endswith(item):
                return False

        punctuation_blacklist = [
            ".",
            "?",
            "!",
            "。",
            "；",
            "？",
            "！",
            "…",
            "〰",
            "〜",
            "～",
            "！",
        ]
        return any(text.strip().endswith(punct) for punct in punctuation_blacklist)

    def clean_cache(self):
        cache_dir = "./cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)

    def load_and_apply_config(self, config_file: str) -> None:
        """
        Load and apply the selected configuration settings from the alternative configuration file.

        Parameters:
        - config_file (str): The path to the alternative configuration file.
        """
        with open(config_file, "r", encoding="utf-8") as file:
            new_config = yaml.safe_load(file)

        # Update the current configuration with the new settings
        self.config.update(new_config)

        # Reinitialize components with the new configuration
        self.live2d = self.init_live2d()
        self.asr = self.init_asr()
        self.tts = self.init_tts()
        self.translator = self.init_translator()
        self.llm = self.init_llm()

    def init_translator(self) -> TranslateInterface | None:
        """
        Initialize the translator based on the configuration.

        Returns:
        - TranslateInterface or None: The initialized translator or None if not enabled.
        """
        if self.config.get("TRANSLATE_AUDIO", False):
            try:
                translate_provider = self.config.get("TRANSLATE_PROVIDER", "DeepLX")
                translator = TranslateFactory.get_translator(
                    translate_provider=translate_provider,
                    **self.config.get(translate_provider, {}),
                )
                return translator
            except Exception as e:
                print(f"Error initializing Translator: {e}")
                print("Proceed without Translator.")
                return None
        else:
            return None


def load_config_with_env(path) -> dict:
    """
    Load the configuration file with environment variables.

    Parameters:
    - path (str): The path to the configuration file.

    Returns:
    - dict: The configuration dictionary.

    Raises:
    - FileNotFoundError if the configuration file is not found.
    - yaml.YAMLError if the configuration file is not a valid YAML file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    # Try common encodings first
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "ascii"]
    content = None

    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as file:
                content = file.read()
                break
        except UnicodeDecodeError:
            continue

    if content is None:
        # Try detecting encoding as last resort
        try:
            with open(path, "rb") as file:
                raw_data = file.read()
            detected = chardet.detect(raw_data)
            if detected["encoding"]:
                content = raw_data.decode(detected["encoding"])
        except Exception as e:
            logger.error(f"Error detecting encoding for config file {path}: {e}")
            raise UnicodeError(f"Failed to decode config file {path} with any encoding")

    # Match ${VAR_NAME}
    pattern = re.compile(r"\$\{(\w+)\}")

    # replace ${VAR_NAME} with os.getenv('VAR_NAME')
    def replacer(match):
        env_var = match.group(1)
        return os.getenv(env_var, match.group(0))

    content = pattern.sub(replacer, content)

    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML from {path}: {e}")
        raise


if __name__ == "__main__":

    logger.add(sys.stderr, level="DEBUG")

    config = load_config_with_env("conf.yaml")

    vtuber_main = OpenLLMVTuberMain(config)

    atexit.register(vtuber_main.clean_cache)

    def _interrupt_on_i():
        while input(">>> say i and press enter to interrupt: ") == "i":
            print("\n\n!!!!!!!!!! interrupt !!!!!!!!!!!!...\n")
            print("Heard sentence: ", vtuber_main.heard_sentence)
            vtuber_main.interrupt(vtuber_main.heard_sentence)

    if config.get("VOICE_INPUT_ON", False):
        threading.Thread(target=_interrupt_on_i).start()

    print("tts on: ", vtuber_main.config.get("TTS_ON", False))
    while True:
        try:
            vtuber_main.conversation_chain()
        except InterruptedError as e:
            print(f"😢Conversation was interrupted. {e}")
            continue
