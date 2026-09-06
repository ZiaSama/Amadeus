"""Offscreen smoke test; Windows compositor behavior still needs desktop QA."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.pet_window import PetWindow

ROOT = Path(__file__).resolve().parents[1]


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_render_interact_drag_and_restart(self):
        config = json.loads((ROOT / "config/behavior.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            window = PetWindow(config, data, debug=True)
            window.show()
            QTest.qWait(100)
            self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
            image = window.grab().toImage()
            self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
            self.assertGreater(image.pixelColor(140, 180).alpha(), 200)
            output = ROOT / "artifacts"
            output.mkdir(exist_ok=True)
            self.assertTrue(image.save(str(output / "placeholder-preview.png")))
            for _ in range(8):
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(140, 180))
            self.assertEqual(window.controller.state.behavior, "evade")
            QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(140, 180))
            QTest.mouseMove(window, QPoint(175, 205), delay=10)
            self.assertTrue(window.controller.state.dragging)
            QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(175, 205))
            self.assertFalse(window.controller.state.dragging)
            self.assertEqual(window.controller.state.click_count, 8)
            window.toggle_on_top(False)
            previous = window.pos()
            window.close()
            restored = PetWindow(config, data)
            self.assertEqual(restored.pos(), previous)
            self.assertFalse(restored.always_on_top)
            log = [json.loads(line) for line in (data / "events.jsonl").read_text().splitlines()]
            self.assertEqual(len(log), 10)
            restored.close()


if __name__ == "__main__":
    unittest.main()
