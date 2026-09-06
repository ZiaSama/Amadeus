from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from brain.local_llm import LocalLLM
from brain.types import CharacterReply
from voice.recorder import AudioRecorder
from voice.stt import FasterWhisperSTT
from voice.tts import LocalTTS


class VoicePipeline(QObject):
    status_changed = Signal(str)
    transcript_ready = Signal(str)
    reply_ready = Signal(object)
    error = Signal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.recorder = AudioRecorder(
            sample_rate=int(config.get("audio", {}).get("sample_rate", 16000)),
            channels=1,
        )
        self.stt = FasterWhisperSTT(config.get("stt", {}))
        self.llm = LocalLLM(config.get("llm", {}))
        self.tts = LocalTTS(config.get("tts", {}))
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="amadeus-voice")
        self.recording = False

    def start_recording(self) -> None:
        if self.recording:
            return
        try:
            self.recorder.start()
            self.recording = True
            self.status_changed.emit("listening")
        except Exception as exc:
            self.error.emit(str(exc))

    def stop_and_process(self, irritation: float, behavior: str) -> None:
        if not self.recording:
            return
        try:
            wav_path = self.recorder.stop_to_wav()
        except Exception as exc:
            self.recording = False
            self.error.emit(str(exc))
            return
        self.recording = False
        self.executor.submit(self._process, wav_path, irritation, behavior)

    def _process(self, wav_path: Path, irritation: float, behavior: str) -> None:
        try:
            if not self.stt.is_loaded:
                self.status_changed.emit("loading_stt")
                self.stt.load()
            self.status_changed.emit("transcribing")
            text = self.stt.transcribe(wav_path)
            self.transcript_ready.emit(text)
            self.status_changed.emit("thinking")
            reply: CharacterReply = self.llm.reply(text, irritation, behavior)
            self.reply_ready.emit(reply)
            self.status_changed.emit("speaking")
            self.tts.speak(reply.text)
            self.status_changed.emit("idle")
        except Exception as exc:
            self.error.emit(str(exc))
            self.status_changed.emit("idle")
        finally:
            try:
                wav_path.unlink(missing_ok=True)
            except OSError:
                pass

    def close(self) -> None:
        self.recorder.cancel()
        self.executor.shutdown(wait=False, cancel_futures=True)
