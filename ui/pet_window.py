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


class PetWindow(QWidget):
    def __init__(self, config: dict, data_dir: Path, debug: bool = False):
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
        self.setToolTip("拖动移动 · 右键菜单 · 连续点击观察反应")
        self.started = self.last_tick = time.monotonic()
        self.controller = CharacterController(config, self.started)
        self.bus = EventBus()
        for kind in ("PET_CLICK", "PET_DRAG_START", "PET_DRAG_END"):
            self.bus.subscribe(kind, self.controller.handle)
        self.press_global: QPoint | None = None
        self.press_origin = QPoint()
        self.debug = QLabel(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.debug.setWindowTitle("Amadeus · 调试")
        self.debug.setMinimumSize(350, 230)
        self.debug.setStyleSheet("background:#162231;color:#dfeaf2;padding:18px;font:13px 'Microsoft YaHei';")
        self.debug.setTextFormat(Qt.TextFormat.PlainText)
        if debug:
            self.debug.show()
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
                "PRESENCE / 交互原型\n\n"
                f"事件：{s.last_event}\n行为：{s.behavior}\n"
                f"不耐烦：{s.irritation:.3f}  /  点击：{s.click_count}\n"
                f"眼睛：{s.eye_x:.2f}  头部：{s.head_x:.2f}\n"
                f"最近事件说明：{s.reason}\n\n"
                "占位绘制 · 无 Live2D · 无台词 · 无系统感知"
            )
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        draw_character(painter, self.controller.state, time.monotonic() - self.started)
        painter.end()

    def emit_event(self, kind: str):
        event = Event(kind, time.monotonic())
        self.bus.emit(event)
        # A bounded local log of interactions only; no desktop titles or input text.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        log = self.data_dir / "events.jsonl"
        if log.exists() and log.stat().st_size > 1_000_000:
            log.replace(self.data_dir / "events.previous.jsonl")
        s = self.controller.state
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": time.time(), "event": kind, "behavior": s.behavior, "irritation": s.irritation}, ensure_ascii=False) + "\n")

    def mousePressEvent(self, event):
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
        # Qt replaces the second press with a double-click event.
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
        self.persist()
        self.debug.close()
        event.accept()
        QApplication.instance().quit()
