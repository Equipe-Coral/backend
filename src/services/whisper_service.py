from src.core.whisper_model import whisper_singleton
import logging

logger = logging.getLogger(__name__)

async def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes audio using the local Faster-Whisper model.
    """
    try:
        model = whisper_singleton.get_model()
        
        # Run transcription in a thread pool since it's CPU bound and blocking
        # For async FastAPI, we usually want to offload this. 
        # However, faster-whisper releases GIL, so it might be okay.
        # But to be safe and keep event loop responsive:
        import asyncio
        from functools import partial
        
        loop = asyncio.get_event_loop()
        
        def _run_transcribe():
            segments, info = model.transcribe(
                audio_path,
                language="pt",
                beam_size=5,
                vad_filter=True
            )
            return " ".join([segment.text for segment in segments])

        text = await loop.run_in_executor(None, _run_transcribe)
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error in transcription: {e}")
        raise
