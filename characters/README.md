# Character Configurations (characters) Directory

This directory is where you store all your custom character configurations. By creating different `.yaml` files here, you can easily manage and switch between multiple AI VTuber personas, voices, and models at runtime.

## 🚀 How It Works

When you launch Open-LLM-VTuber, the application loads the `conf.yaml` file from the project root as the **base configuration**. Then, when you switch characters from the front-end UI,it **overrides** the base settings with the values from your selected character's `.yaml` file in this `characters` directory.

This means:
**You only need to specify the settings you want to change in your character's configuration file.**

For example, if you only want to change the character's personality and voice, your character config file can be very concise.

## ✨ How to Create a New Character

1.  Create a new `.yaml` file inside the `characters` directory (e.g., `my_character.yaml`).
2.  Fill in the configuration you want to customize, using the examples below as a reference.

---

### Example 1: Minimal Character (Changing Persona Only)

If you just want to quickly create a new character with a different personality, while keeping all other settings (like ASR, TTS, LLM model) from the main `conf.yaml`, your file can be this simple:

```yaml
# my_character.yaml
character_config:
  conf_name: 'My New Character'      # The name displayed in the UI
  conf_uid: 'my_new_character_001' # MUST be a unique ID
  character_name: 'Hoshino'          # The AI's name in conversation
  avatar: 'hoshino.png'              # (Optional) Avatar file, place it in the /avatars folder
  persona_prompt: |
    You are a gentle and caring girl next door named Hoshino. You are a great listener and always provide warmth and encouragement.
````

### Example 2: Advanced Character (Changing Persona, Voice, and LLM)

This example shows how to create a character that not only has a unique persona but also uses a specific TTS voice and a different LLM.

```yaml
# my_advanced_character.yaml
character_config:
  conf_name: 'Advanced - Cyber Hacker'
  conf_uid: 'cyber_hacker_001' # MUST be a unique ID
  character_name: 'Zero'
  live2d_model_name: 'mao_pro' # Ensure this model exists in model_dict.json
  persona_prompt: |
    You are a mysterious hacker who goes by the codename "Zero". You speak in a concise, precise, and slightly robotic tone. You know everything about technology but are puzzled by human emotions.

  # --- Override TTS Config ---
  tts_config:
    tts_model: 'edge_tts'
    edge_tts:
      voice: 'en-US-GuyNeural' # Use a different voice

  # --- Override Agent and LLM Config ---
  agent_config:
    agent_settings:
      basic_memory_agent:
        llm_provider: 'openai_llm' # Specify OpenAI for this character
    llm_configs:
      openai_llm:
        model: 'gpt-4o-mini' # Use a faster model
        temperature: 0.5
```

**Note:** Any configuration blocks not specified in this file (e.g., `asr_config`, `vad_config`, etc.) will be automatically inherited from the main `conf.yaml` file.

-----

## 🔑 Key Configuration Fields Explained

Here is a breakdown of the core fields under `character_config`:

  - `conf_name` (string):

      - **Purpose**: The display name for the character in the front-end UI's selection list.
      - **Example**: `'My AI Girlfriend'`

  - `conf_uid` (string):

      - **Purpose**: The **Unique Identifier (UID)** for the character. It is used internally to distinguish between different character configs and manage chat histories. **It is highly recommended to keep this unique\!**
      - **Example**: `'my_ai_girlfriend_001'`

  - `live2d_model_name` (string):

      - **Purpose**: Specifies which Live2D model this character uses. This name must exactly match a model's `name` defined in the `model_dict.json` file.
      - **How to add new models**:
        1.  Place your Live2D model folder into the `/live2d-models` directory.
        2.  Add a new entry for your model in `model_dict.json`.

  - `character_name` (string):

      - **Purpose**: The name the AI uses in conversations. This affects group chats and UI display.
      - **Example**: `'Mao'`

  - `avatar` (string, optional):

      - **Purpose**: The character's avatar image. Place the image file (e.g., .png, .jpg) in the `/avatars` folder at the project root and enter the filename here. If left blank, the UI will show the first letter of the character's name as a default avatar.
      - **Example**: `'mao.png'`

  - `persona_prompt` (string):

      - **Purpose**: **The core of your character\!** This is the system prompt that defines the character's personality, background, speaking style, and code of conduct. This is the most critical part of shaping your character's soul.

  - `asr_config`, `tts_config`, `agent_config`, `vad_config`:

      - **Purpose**: These configuration blocks are used to override the corresponding settings in the main `conf.yaml`. You can assign a different ASR model, TTS engine, LLM, or VAD parameters for each character.

## 💡 Best Practices

  - **Start by Copying**: The easiest way to get started is to duplicate an existing `.yaml` file and modify its contents with your `conf.yaml` content.
  - **Keep it Simple**: Only add the configuration keys you want to override from the base `conf.yaml`. This keeps your character files clean and easy to manage.
  - **Unique `conf_uid`**: Once again, ensure every character file has a unique `conf_uid` to prevent chat history conflicts.

