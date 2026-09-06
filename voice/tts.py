class LocalTTS:
    def __init__(self, config: dict):
        self.rate = int(config.get("rate", 185))
        self.volume = float(config.get("volume", 1.0))
        self.voice_contains = str(config.get("voice_contains", "")).lower()
        self._engine = None

    def _ensure_engine(self):
        if self._engine is not None:
            return
        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("缺少 pyttsx3；请安装 requirements-voice.txt") from exc
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", self.rate)
        self._engine.setProperty("volume", self.volume)
        if self.voice_contains:
            for voice in self._engine.getProperty("voices"):
                haystack = f"{voice.id} {voice.name}".lower()
                if self.voice_contains in haystack:
                    self._engine.setProperty("voice", voice.id)
                    break

    def speak(self, text: str) -> None:
        self._ensure_engine()
        self._engine.say(text)
        self._engine.runAndWait()
