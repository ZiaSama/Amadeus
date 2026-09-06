import json
from pathlib import Path
import time

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QCursor, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QWidget

from character.controller import CharacterController
from core.events import Event, EventBus
from storage.settings import load_settings, save_settings
from ui.placeholder import draw_character
from voice.pipeline import VoicePipeline


class PetWindow(QWidget):
    def __init__(
        self,
        config: dict,
        data_dir: Path,
        debug: bool = False,
        voice_config: dict | None = None,
    ):
        super().__init__()
        self.config, self.data_dir = config, data_dir
        self.settings_path = data_dir / "settings.json"
        settings = load_settings(self.settings_path)
        self.always_on_top = settings.get("always_on_top", True)
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Amadeus — Presence 原型")
        self.setFixedSize(280, 340)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("左键拖动/点击 · 按住中键说话 · 右键菜单")
        self.started = self.last_tick = time.monotonic()
        self.controller = CharacterController(config, self.started)
        self.bus = EventBus()
        for kind in (
            "PET_CLICK", "PET_DRAG_START", "PET_DRAG_END",
            "VOICE_LISTENING", "VOICE_TRANSCRIBING", "VOICE_THINKING",
            "VOICE_REPLY", "VOICE_IDLE", "VOICE_ERROR",
        ):
            self.bus.subscribe(kind, self.controller.handle)
        self.press_global: QPoint | None = None
        self.press_origin = QPoint()
        self.last_transcript = ""

        self.debug = QLabel(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.debug.setWindowTitle("Amadeus · 调试")
        self.debug.setMinimumSize(380, 260)
        self.debug.setStyleSheet("background:#162231;color:#dfeaf2;padding:18px;font:13px 'Microsoft YaHei';")
        self.debug.setTextFormat(Qt.TextFormat.PlainText)
        if debug:
            self.debug.show()

        self.voice: VoicePipeline | None = None
        if voice_config and voice_config.get("enabled", False):
            self.voice = VoicePipeline(voice_config)
            self.voice.status_changed.connect(self.on_voice_status)
            self.voice.transcript_ready.connect(self.on_transcript)
            self.voice.reply_ready.connect(self.on_voice_reply)
            self.voice.error.connect(self.on_voice_error)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(settings.get("x", screen.right() - self.width() - 32), settings.get("y", screen.bottom() - self.height() - 20))
        self.clamp_to_screen()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(config["frame_ms"])
        app = QApplication.instance()
        app.screenAdded.connect(lambda _: self.clamp_to_screen())
        app.screenRemoved.connect(lambda _: self.clamp_to_screen())

    def clamp_to_screen(self):
        center = self.frameGeometry().center()
        screen = QApplication.screenAt(center) or QApplication.primaryScreen()
        rect = screen.availableGeometry()
        x = max(rect.left(), min(self.x(), rect.right() - self.width() + 1))
        y = max(rect.top(), min(self.y(), rect.bottom() - self.height() + 1))
        self.move(x, y)

    def tick(self):
        now = time.monotonic()
        dt, self.last_tick = now - self.last_tick, now
        cursor = self.mapFromGlobal(QCursor.pos())
        self.controller.tick(now, dt, (cursor.x() - 140, cursor.y() - 153))
        if self.debug.isVisible():
            s = self.controller.state
            self.debug.setText(
                "PRESENCE / 本地语音原型\n\n"
                f"事件：{s.last_event}\n行为：{s.behavior}\n表情：{s.expression}\n"
                f"语音：{s.voice_status}\n"
                f"不耐烦：{s.irritation:.3f}  /  点击：{s.click_count}\n"
                f"眼睛：{s.eye_x:.2f}  头部：{s.head_x:.2f}\n"
                f"最近事件说明：{s.reason}\n"
                f"识别文本：{self.last_transcript or '-'}\n"
                f"角色回复：{s.speech_text or '-'}\n\n"
                "按住鼠标中键说话；STT/LLM/TTS 在后台线程运行。"
            )
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        draw_character(painter, self.controller.state, time.monotonic() - self.started)
        painter.end()

    def emit_event(self, kind: str, payload: dict | None = None):
        event = Event(kind, time.monotonic(), payload=payload or {})
        self.bus.emit(event)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        log = self.data_dir / "events.jsonl"
        if log.exists() and log.stat().st_size > 1_000_000:
            log.replace(self.data_dir / "events.previous.jsonl")
        s = self.controller.state
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "time": time.time(),
                "event": kind,
                "behavior": s.behavior,
                "expression": s.expression,
                "irritation": s.irritation,
            }, ensure_ascii=False) + "\n")

    def on_voice_status(self, status: str):
        mapping = {
            "listening": "VOICE_LISTENING",
            "transcribing": "VOICE_TRANSCRIBING",
            "thinking": "VOICE_THINKING",
            "idle": "VOICE_IDLE",
        }
        kind = mapping.get(status)
        if kind:
            self.emit_event(kind)

    def on_transcript(self, text: str):
        self.last_transcript = text

    def on_voice_reply(self, reply):
        self.emit_event("VOICE_REPLY", {"text": reply.text, "emotion": reply.emotion})

    def on_voice_error(self, message: str):
        self.emit_event("VOICE_ERROR", {"message": message})
        if self.debug.isVisible():
            self.debug.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.voice is None:
                self.emit_event("VOICE_ERROR", {"message": "语音模式未启用"})
            else:
                self.voice.start_recording()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_global = event.globalPosition().toPoint()
            self.press_origin = self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.press_global is None:
            return
        delta = event.globalPosition().toPoint() - self.press_global
        if not self.controller.state.dragging and delta.manhattanLength() >= QApplication.startDragDistance():
            self.emit_event("PET_DRAG_START")
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        if self.controller.state.dragging:
            self.move(self.press_origin + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.voice is not None:
                s = self.controller.state
                self.voice.stop_and_process(s.irritation, s.behavior)
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton or self.press_global is None:
            return
        if self.controller.state.dragging:
            self.emit_event("PET_DRAG_END")
            self.clamp_to_screen()
            self.persist()
        else:
            self.emit_event("PET_CLICK")
        self.press_global = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        debug = menu.addAction("调试面板")
        debug.setCheckable(True)
        debug.setChecked(self.debug.isVisible())
        debug.triggered.connect(self.debug.setVisible)
        top = menu.addAction("始终置顶")
        top.setCheckable(True)
        top.setChecked(self.always_on_top)
        top.triggered.connect(self.toggle_on_top)
        voice = menu.addAction("语音：按住鼠标中键")
        voice.setEnabled(False)
        if self.voice is None:
            voice.setText("语音：未启用")
        menu.addSeparator()
        menu.addAction("退出", self.close)
        menu.exec(event.globalPos())

    def toggle_on_top(self, enabled):
        self.always_on_top = enabled
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.show()
        self.persist()

    def persist(self):
        save_settings(self.settings_path, {"x": self.x(), "y": self.y(), "always_on_top": self.always_on_top})

    def closeEvent(self, event):
        self.timer.stop()
        if self.voice is not None:
            self.voice.close()
        self.persist()
        self.debug.close()
        event.accept()
        QApplication.instance().quit()
