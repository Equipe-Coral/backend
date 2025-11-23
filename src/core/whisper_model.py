from faster_whisper import WhisperModel
from src.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

class WhisperModelSingleton:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_model(self):
        if self._model is None:
            logger.info("Loading Whisper model... This might take a while.")
            try:
                model_size = os.getenv("WHISPER_MODEL", "base")
                device = os.getenv("WHISPER_DEVICE", "cpu")
                compute_type = "int8" if device == "cpu" else "float16"
                
                self._model = WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type
                )
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise
        return self._model

whisper_singleton = WhisperModelSingleton()
