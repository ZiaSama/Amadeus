import json
import math
from pathlib import Path
import random
import tempfile
import unittest

from brain.history import ConversationHistory
from brain.local_llm import LocalLLM
from brain.types import CharacterReply
from character.controller import CharacterController
from core.events import Event, EventBus
from storage.settings import load_settings, save_settings

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config/behavior.json").read_text())


class InteractionTests(unittest.TestCase):
    def make_controller(self):
        return CharacterController(CONFIG, 0, random.Random(7))

    def test_click_escalation_and_expired_window(self):
        model = self.make_controller()
        for i in range(8):
            model.handle(Event("PET_CLICK", i * 0.2))
        self.assertEqual(model.state.behavior, "evade")
        model.tick(12, 10, (0, 0))
        self.assertEqual(model.state.click_count, 0)
        self.assertEqual(model.state.behavior, "idle")
        self.assertGreater(model.state.irritation, 0.5)

    def test_emotion_decay_is_frame_rate_independent(self):
        one, many = self.make_controller(), self.make_controller()
        one.state.irritation = many.state.irritation = 0.8
        one.tick(180, 180, (0, 0))
        for second in range(1, 181):
            many.tick(second, 1, (0, 0))
        self.assertAlmostEqual(one.state.irritation, 0.05 + 0.75 / math.e)
        self.assertAlmostEqual(one.state.irritation, many.state.irritation)

    def test_drag_does_not_count_as_click(self):
        model = self.make_controller()
        model.handle(Event("PET_DRAG_START", 1))
        model.tick(10, 9, (20, 20))
        self.assertEqual(model.state.behavior, "dragged")
        model.handle(Event("PET_DRAG_END", 11))
        self.assertFalse(model.state.dragging)
        self.assertEqual(model.state.click_count, 0)

    def test_eye_leads_head(self):
        model = self.make_controller()
        model.tick(0.1, 0.1, (180, 0))
        self.assertGreater(model.state.eye_x, model.state.head_x)
        self.assertLess(model.state.eye_x, 1)

    def test_bus_delivers_only_subscribed_events(self):
        bus, received = EventBus(), []
        bus.subscribe("PET_CLICK", received.append)
        bus.emit(Event("PET_DRAG_START", 0))
        bus.emit(Event("PET_CLICK", 1, payload={"x": 1}))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["x"], 1)

    def test_voice_reply_updates_character_state(self):
        model = self.make_controller()
        model.handle(Event("VOICE_LISTENING", 1))
        self.assertEqual(model.state.voice_status, "listening")
        self.assertEqual(model.state.expression, "curious")
        model.handle(Event("VOICE_REPLY", 2, payload={"text": "……嗯？", "emotion": "skeptical"}))
        self.assertEqual(model.state.voice_status, "speaking")
        self.assertEqual(model.state.speech_text, "……嗯？")
        self.assertEqual(model.state.expression, "skeptical")

    def test_short_history_is_bounded(self):
        history = ConversationHistory(max_turns=2)
        for i in range(4):
            history.add_user(f"u{i}")
            history.add_assistant(f"a{i}")
        self.assertEqual(len(history.messages()), 4)
        self.assertEqual(history.messages()[0]["content"], "u2")

    def test_llm_reply_parser_accepts_json_and_plain_text(self):
        parsed = LocalLLM._parse_reply('{"text":"好了。","emotion":"confident"}')
        self.assertEqual(parsed.text, "好了。")
        self.assertEqual(parsed.emotion, "confident")
        fallback = LocalLLM._parse_reply("直接回复")
        self.assertEqual(fallback.text, "直接回复")
        self.assertEqual(fallback.emotion, "neutral")

    def test_style_guard_removes_customer_service_greeting(self):
        reply = CharacterReply(text="你好！有什么可以帮助你的吗？", emotion="neutral")
        guarded = LocalLLM._style_guard("你好", reply)
        self.assertNotIn("帮助你", guarded.text)
        self.assertEqual(guarded.text, "……你好。突然这么正式干什么？")
        self.assertEqual(guarded.emotion, "skeptical")

    def test_style_guard_preserves_normal_character_reply(self):
        reply = CharacterReply(text="又来？先把报错给我看。", emotion="mild_annoyed")
        guarded = LocalLLM._style_guard("代码又错了", reply)
        self.assertEqual(guarded, reply)

    def test_settings_roundtrip_and_corrupt_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_settings(path, {"x": -300, "y": 20, "always_on_top": False})
            self.assertEqual(load_settings(path)["x"], -300)
            self.assertFalse(load_settings(path)["always_on_top"])
            path.write_text('{"x": "invalid", "always_on_top": "false"}')
            self.assertEqual(load_settings(path), {})
            path.write_text("broken")
            self.assertEqual(load_settings(path), {})


if __name__ == "__main__":
    unittest.main()
