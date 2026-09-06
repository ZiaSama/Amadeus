import os
from pathlib import Path


class FasterWhisperSTT:
    def __init__(self, config: dict):
        self.model_size = config.get("model", "small")
        self.device = config.get("device", "cpu")
        self.compute_type = config.get("compute_type", "int8")
        self.language = config.get("language", "zh")
        self.beam_size = int(config.get("beam_size", 3))
        self.vad_filter = bool(config.get("vad_filter", False))
        self.condition_on_previous_text = bool(config.get("condition_on_previous_text", False))
        self.initial_prompt = str(config.get("initial_prompt", "")).strip() or None
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
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            condition_on_previous_text=self.condition_on_previous_text,
            initial_prompt=self.initial_prompt,
            temperature=0.0,
        )
        text = "".join(segment.text for segment in segments).strip()
        if not text:
            raise RuntimeError("没有识别到有效语音；请按住中键后再开始说话，并尽量保持 0.5 秒以上")
        return text
