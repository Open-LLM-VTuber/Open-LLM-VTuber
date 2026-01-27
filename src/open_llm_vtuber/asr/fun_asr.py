import io
import os
import re
import torch
import numpy as np
import soundfile as sf
from funasr import AutoModel
from .asr_interface import ASRInterface
from typing import Optional

# Try to import modelscope for local cache detection
try:
    from modelscope.hub.snapshot_download import snapshot_download

    MODEL_SCOPE_DOWNLOAD_AVAILABLE = True
except ImportError:
    print("Warning: Unable to import modelscope.hub.snapshot_download.")
    MODEL_SCOPE_DOWNLOAD_AVAILABLE = False

# Model alias to actual ModelScope ID mapping table
MODEL_ALIAS_TO_FULL_ID_MAP = {
    "paraformer-zh": "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "paraformer-zh-spk": "iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn",
    "paraformer-zh-online": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
    "paraformer-en": "iic/speech_paraformer-large-vad-punc_asr_nat-en-16k-common-vocab10020",
    "conformer-en": "iic/speech_conformer_asr-en-16k-vocab4199-pytorch",
    "ct-punc": "iic/punc_ct-transformer_cn-en-common-vocab471067-large",
    "fsmn-vad": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "fa-zh": "iic/speech_timestamp_prediction-v1-16k-offline",
    "SenseVoiceSmall": "iic/SenseVoiceSmall",
    "iic/SenseVoiceSmall": "iic/SenseVoiceSmall",
}


# paraformer-zh is a multi-functional asr model
# use vad, punc, spk or not as you need


class VoiceRecognition(ASRInterface):
    def __init__(
        self,
        model_name: str = "iic/SenseVoiceSmall",
        language: str = "auto",
        vad_model: str = "fsmn-vad",
        punc_model: str = "ct-punc",
        ncpu: int = None,
        hub: str = None,
        device: str = "cpu",
        disable_update: bool = True,
        sample_rate: int = 16000,
        use_itn: bool = False,
    ) -> None:
        # Resolve model paths
        final_model_input = self._get_final_model_input(model_name)
        final_vad_input = self._get_final_model_input(vad_model) if vad_model else None
        final_punc_input = (
            self._get_final_model_input(punc_model) if punc_model else None
        )

        self.model = AutoModel(
            model=final_model_input,
            vad_model=final_vad_input,
            ncpu=ncpu,
            hub=hub,
            device=device,
            disable_update=disable_update,
            punc_model=final_punc_input,
            # spk_model="cam++",
        )
        self.SAMPLE_RATE = sample_rate
        self.use_itn = use_itn
        self.language = language

    def _get_final_model_input(self, alias_or_id: Optional[str]) -> Optional[str]:
        """
        Process model input function:
        1. Check mapping table to get canonical ModelScope ID.
        2. Try to get local path using snapshot_download.
        3. If local path is valid, return local path, otherwise return canonical ModelScope ID.
        """
        if not alias_or_id:
            return None

        # Get canonical ModelScope ID from mapping table
        resolved_id = MODEL_ALIAS_TO_FULL_ID_MAP.get(alias_or_id, alias_or_id)
        final_input_for_automodel = resolved_id  # Default to use resolved ID

        # Try to get local path using snapshot_download
        if MODEL_SCOPE_DOWNLOAD_AVAILABLE:
            try:
                local_path = snapshot_download(resolved_id, local_files_only=True)
                if os.path.exists(local_path):  # Double check path exists
                    final_input_for_automodel = local_path  # Use local path if found
                    # print(f"Successfully resolved '{resolved_id}' to local path: {local_path}")
            except ValueError:
                # Not found in local cache, use original ID
                pass
            except Exception as e:
                print(f"Error occurred while checking '{resolved_id}': {e}")

        return final_input_for_automodel

    def transcribe_np(self, audio: np.ndarray) -> str:
        audio_tensor = torch.tensor(audio, dtype=torch.float32)

        res = self.model.generate(
            input=audio_tensor,
            batch_size_s=300,
            use_itn=self.use_itn,
            language=self.language,
        )

        full_text = res[0]["text"]

        # SenseVoiceSmall may spits out some tags
        # like this: '<|zh|><|NEUTRAL|><|Speech|><|woitn|>欢迎大家来体验达摩院推出的语音识别模型'
        # we should remove those tags from the result

        # remove tags
        full_text = re.sub(r"<\|.*?\|>", "", full_text)
        # the tags can also look like '< | en | > < | EMO _ UNKNOWN | > < | S pe ech | > < | wo itn | > ', so...
        full_text = re.sub(r"< \|.*?\| >", "", full_text)

        return full_text.strip()

    def _numpy_to_wav_in_memory(self, numpy_array: np.ndarray, sample_rate):
        memory_file = io.BytesIO()
        sf.write(memory_file, numpy_array, sample_rate, format="WAV")
        memory_file.seek(0)

        return memory_file
