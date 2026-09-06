from pathlib import Path


class FasterWhisperSTT:
    def __init__(self, config: dict):
        self.model_size = config.get("model", "small")
        self.device = config.get("device", "cuda")
        self.compute_type = config.get("compute_type", "int8_float16")
        self.language = config.get("language", "zh")
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("缺少 faster-whisper；请安装 requirements-voice.txt") from exc
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
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
