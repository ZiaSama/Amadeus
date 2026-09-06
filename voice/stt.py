import os
from pathlib import Path


class FasterWhisperSTT:
    def __init__(self, config: dict):
        self.model_size = config.get("model", "base")
        self.device = config.get("device", "cuda")
        self.compute_type = config.get("compute_type", "int8_float16")
        self.language = config.get("language", "zh")
        cache_dir = str(config.get("cache_dir", "")).strip()
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        self._ensure_model()

    def _ensure_model(self):
        if self._model is not None:
            return

        # Do not rely on the caller's shell environment for the model location.
        # faster-whisper forwards download_root to the Hugging Face cache layer.
        download_root = None
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            download_root = str(self.cache_dir)
            os.environ["HF_HUB_CACHE"] = download_root
            os.environ["HF_HOME"] = str(self.cache_dir.parent)
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("缺少 faster-whisper；请安装 requirements-voice.txt") from exc

        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            download_root=download_root,
        )

    def transcribe(self, wav_path: Path) -> str:
        self._ensure_model()
        segments, _ = self._model.transcribe(
            str(wav_path),
            language=self.language,
            vad_filter=True,
            beam_size=1,
        )
        text = "".join(segment.text for segment in segments).strip()
        if not text:
            raise RuntimeError("没有识别到有效语音")
        return text
