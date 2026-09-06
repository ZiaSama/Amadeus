from pathlib import Path
import tempfile
import wave


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        silence_padding_ms: int = 180,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_padding_ms = max(0, int(silence_padding_ms))
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

        raw = b"".join(self._frames)
        self._frames.clear()
        if not raw:
            raise RuntimeError("没有录到音频；请检查 Windows 麦克风权限和默认输入设备")

        bytes_per_frame = 2 * self.channels  # int16
        captured_frames = len(raw) // bytes_per_frame
        duration_sec = captured_frames / self.sample_rate
        if duration_sec < 0.20:
            raise RuntimeError(f"录音太短（{duration_sec:.2f}s）；请按住中键后再说话")

        padding_frames = int(self.sample_rate * self.silence_padding_ms / 1000)
        silence = b"\x00" * (padding_frames * bytes_per_frame)
        raw = silence + raw + silence

        handle = tempfile.NamedTemporaryFile(prefix="amadeus_", suffix=".wav", delete=False)
        path = Path(handle.name)
        handle.close()
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(raw)
        return path

    def cancel(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._frames.clear()
