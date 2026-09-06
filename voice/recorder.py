from pathlib import Path
import tempfile
import wave


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._stream = None
        self._frames: list[bytes] = []

    def start(self) -> None:
        if self._stream is not None:
            return
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("缺少 sounddevice；请安装 requirements-voice.txt") from exc

        self._frames.clear()

        def callback(indata, frames, time_info, status):  # sounddevice callback signature
            self._frames.append(indata.copy().tobytes())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=callback,
        )
        self._stream.start()

    def stop_to_wav(self) -> Path:
        if self._stream is None:
            raise RuntimeError("录音尚未开始")
        self._stream.stop()
        self._stream.close()
        self._stream = None

        handle = tempfile.NamedTemporaryFile(prefix="amadeus_", suffix=".wav", delete=False)
        path = Path(handle.name)
        handle.close()
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(2)  # int16
            wav.setframerate(self.sample_rate)
            wav.writeframes(b"".join(self._frames))
        self._frames.clear()
        return path

    def cancel(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._frames.clear()
