class LocalTTS:
    def __init__(self, config: dict):
        self.rate = int(config.get("rate", 185))
        self.volume = float(config.get("volume", 1.0))
        self.voice_contains = str(config.get("voice_contains", "")).lower()
        self.recreate_engine_each_utterance = bool(config.get("recreate_engine_each_utterance", True))
        self._engine = None

    def _create_engine(self):
        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("缺少 pyttsx3；请安装 requirements-voice.txt") from exc
        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)
        if self.voice_contains:
            for voice in engine.getProperty("voices"):
                haystack = f"{voice.id} {voice.name}".lower()
                if self.voice_contains in haystack:
                    engine.setProperty("voice", voice.id)
                    break
        return engine

    def _ensure_engine(self):
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def speak(self, text: str) -> None:
        # pyttsx3/SAPI can become silent after the first runAndWait() when an
        # engine is reused from a long-lived worker thread on Windows. A fresh
        # engine per utterance is inexpensive for this lightweight prototype
        # and avoids that stale event-loop state.
        engine = self._create_engine() if self.recreate_engine_each_utterance else self._ensure_engine()
        try:
            engine.say(text)
            engine.runAndWait()
        finally:
            try:
                engine.stop()
            except Exception:
                pass
            if self.recreate_engine_each_utterance:
                del engine
