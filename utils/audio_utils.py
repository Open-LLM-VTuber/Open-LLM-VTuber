import numpy as np
import scipy.io.wavfile as wavfile
from loguru import logger
import os

def save_audio_to_wav(audio_data: np.ndarray, filepath: str, sample_rate: int = 16000, overwrite: bool = False):
    """
    Saves a NumPy array of audio data to a WAV file.

    Args:
        audio_data (np.ndarray): The audio data to save. Should be a 1D or 2D array.
                                 If 2D, assumes shape is (samples, channels).
                                 Values should typically be in the range [-1.0, 1.0] for float,
                                 or within integer range for int types (e.g., int16).
        filepath (str): The path (including filename) to save the WAV file.
        sample_rate (int): The sample rate of the audio data (e.g., 16000, 44100).
        overwrite (bool): If True, overwrite the file if it already exists.
                          If False and file exists, a number will be appended to the filename.

    Returns:
        str: The actual filepath the audio was saved to, or None if saving failed.
    """
    if not isinstance(audio_data, np.ndarray):
        logger.error("Audio data must be a NumPy array.")
        return None

    if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
        # Ensure data is in range [-1, 1] for float, then scale to int16
        # This is a common convention for wavfile.write with float input,
        # but it's safer to explicitly convert to int16 for broader compatibility.
        if np.max(np.abs(audio_data)) > 1.0:
            logger.warning("Audio data is float but exceeds [-1.0, 1.0] range. Clipping may occur.")
            audio_data = np.clip(audio_data, -1.0, 1.0)
        # Convert to int16
        audio_data_int16 = (audio_data * 32767).astype(np.int16)
    elif audio_data.dtype == np.int16:
        audio_data_int16 = audio_data
    elif audio_data.dtype == np.int32:
        # If it's int32, scale down to int16. This might lose precision.
        logger.warning("Audio data is int32. Converting to int16, precision loss may occur.")
        audio_data_int16 = (audio_data / 2**16).astype(np.int16)
    elif audio_data.dtype == np.uint8:
        logger.warning("Audio data is uint8. Converting to int16. This assumes it's centered at 128.")
        audio_data_int16 = (audio_data.astype(np.int16) - 128) * 256 # Scale to int16 range
    else:
        logger.error(f"Unsupported audio data type: {audio_data.dtype}. Please use float32, float64, int16, or int32.")
        return None

    try:
        # Ensure directory exists
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

        final_filepath = filepath
        if not overwrite and os.path.exists(final_filepath):
            base, ext = os.path.splitext(final_filepath)
            i = 1
            while os.path.exists(f"{base}_{i}{ext}"):
                i += 1
            final_filepath = f"{base}_{i}{ext}"
            logger.warning(f"File {filepath} existed. Saving to {final_filepath} instead.")

        wavfile.write(final_filepath, sample_rate, audio_data_int16)
        logger.success(f"Audio saved successfully to {final_filepath} at {sample_rate} Hz.")
        return final_filepath
    except Exception as e:
        logger.error(f"Error saving audio to WAV file {final_filepath if 'final_filepath' in locals() else filepath}: {e}")
        return None

if __name__ == "__main__":
    # Example usage:
    logger.info("Running audio_utils.py example...")

    # Create a dummy session directory for testing
    test_session_dir = "test_chat_history/test_session_audio_utils"
    if not os.path.exists(test_session_dir):
        os.makedirs(test_session_dir)

    # 1. Test with float32 data
    sample_rate_test = 16000
    duration = 2  # seconds
    frequency = 440  # Hz (A4 note)
    t = np.linspace(0, duration, int(sample_rate_test * duration), endpoint=False)
    test_audio_float32 = 0.5 * np.sin(2 * np.pi * frequency * t)
    test_audio_float32 = test_audio_float32.astype(np.float32)

    logger.info(f"Shape: {test_audio_float32.shape}, dtype: {test_audio_float32.dtype}, min: {np.min(test_audio_float32)}, max: {np.max(test_audio_float32)}")
    saved_path_float = save_audio_to_wav(test_audio_float32, os.path.join(test_session_dir, "test_float32.wav"), sample_rate_test)
    if saved_path_float:
        logger.info(f"Float32 audio saved to: {saved_path_float}")

    # 2. Test with int16 data
    test_audio_int16 = (test_audio_float32 * 32767).astype(np.int16)
    logger.info(f"Shape: {test_audio_int16.shape}, dtype: {test_audio_int16.dtype}, min: {np.min(test_audio_int16)}, max: {np.max(test_audio_int16)}")
    saved_path_int = save_audio_to_wav(test_audio_int16, os.path.join(test_session_dir, "test_int16.wav"), sample_rate_test)
    if saved_path_int:
        logger.info(f"Int16 audio saved to: {saved_path_int}")

    # 3. Test overwrite=False (default)
    save_audio_to_wav(test_audio_int16, os.path.join(test_session_dir, "test_int16.wav"), sample_rate_test) # try saving again

    # 4. Test overwrite=True
    saved_path_overwrite = save_audio_to_wav(test_audio_int16, os.path.join(test_session_dir, "test_overwrite.wav"), sample_rate_test, overwrite=True)
    if saved_path_overwrite:
      save_audio_to_wav(test_audio_float32, os.path.join(test_session_dir, "test_overwrite.wav"), sample_rate_test, overwrite=True) # try saving again with different data

    # 5. Test with stereo (2-channel) audio
    test_audio_stereo_float32 = np.array([test_audio_float32, 0.8 * test_audio_float32]).T # Transpose to make it (samples, channels)
    logger.info(f"Stereo Shape: {test_audio_stereo_float32.shape}, dtype: {test_audio_stereo_float32.dtype}")
    saved_path_stereo = save_audio_to_wav(test_audio_stereo_float32, os.path.join(test_session_dir, "test_stereo.wav"), sample_rate_test)
    if saved_path_stereo:
        logger.info(f"Stereo audio saved to: {saved_path_stereo}")

    logger.info(f"Test audio files saved in: {os.path.abspath(test_session_dir)}")
    logger.info("Audio_utils.py example finished.")
