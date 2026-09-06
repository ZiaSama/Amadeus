"""Small deterministic interaction model plus time-based gaze and blinking.

This is the first interaction prototype, not the full Reaction/Utility system.
Time and randomness are supplied by the caller so behavior can be replayed.
"""
from collections import deque
import math
import random

from core.events import Event
from core.state import CharacterState, WorldState


def smooth(current: float, target: float, dt: float, tau: float) -> float:
    return target + (current - target) * math.exp(-dt / tau)


class CharacterController:
    def __init__(self, config: dict, now: float, rng: random.Random | None = None):
        self.config = config
        self.state = CharacterState(irritation=config["irritation_baseline"])
        self.world = WorldState()
        self.rng = rng or random.Random()
        self.clicks: deque[float] = deque()
        self.reaction_until = now
        self.next_blink = now + self.rng.uniform(*config["blink_interval_sec"])
        self.next_idle_gaze = now
        self.idle_target = (0.0, 0.0)

    def handle(self, event: Event) -> None:
        s, c = self.state, self.config
        s.last_event = event.kind
        if event.kind == "PET_CLICK":
            self._prune_clicks(event.timestamp)
            self.clicks.append(event.timestamp)
            s.click_count = len(self.clicks)
            gain = c["click_gain"] if s.click_count == 1 else c["repeat_click_gain"]
            s.irritation = min(1.0, s.irritation + gain)
            if s.irritation >= c["evade_threshold"]:
                s.behavior = "evade"
            elif s.irritation >= c["annoyed_threshold"]:
                s.behavior = "annoyed"
            else:
                s.behavior = "acknowledge"
            s.reason = f"10 秒内点击 {s.click_count} 次；不耐烦 {s.irritation:.2f}"
            self.reaction_until = event.timestamp + c["reaction_sec"]
        elif event.kind == "PET_DRAG_START":
            s.dragging = True
            s.behavior = "dragged"
            s.reason = "拖动中：保持视线跟随"
        elif event.kind == "PET_DRAG_END":
            s.dragging = False
            s.behavior = "idle"
            s.reason = "拖动结束；当前原型不计拖动情绪"

    def _prune_clicks(self, now: float) -> None:
        while self.clicks and now - self.clicks[0] >= self.config["click_window_sec"]:
            self.clicks.popleft()
        self.state.click_count = len(self.clicks)

    def tick(self, now: float, dt: float, cursor: tuple[float, float]) -> None:
        s, c = self.state, self.config
        self._prune_clicks(now)
        s.irritation = smooth(s.irritation, c["irritation_baseline"], dt, c["irritation_tau_sec"])
        if not s.dragging and now >= self.reaction_until:
            s.behavior = "idle"
        x, y = cursor  # Cursor relative to the character's face, in logical pixels.
        near = math.hypot(x, y) < c["cursor_radius_px"]
        self.world = WorldState(x, y, near)
        if now >= self.next_idle_gaze:
            self.idle_target = (self.rng.uniform(-0.35, 0.35), self.rng.uniform(-0.2, 0.2))
            self.next_idle_gaze = now + self.rng.uniform(*c["idle_gaze_interval_sec"])
        target = self.idle_target
        if near or s.dragging or now < self.reaction_until:
            target = (max(-1, min(1, x / 180)), max(-1, min(1, y / 180)))
        for axis, value in zip(("x", "y"), target):
            eye, head = "eye_" + axis, "head_" + axis
            setattr(s, eye, smooth(getattr(s, eye), value, dt, c["eye_tau_sec"]))
            setattr(s, head, smooth(getattr(s, head), value * 0.55, dt, c["head_tau_sec"]))
        phase = (now - self.next_blink) / c["blink_duration_sec"]
        s.eye_open = 1.0
        if 0 <= phase <= 1:
            s.eye_open = abs(phase * 2 - 1)
        elif phase > 1:
            self.next_blink = now + self.rng.uniform(*c["blink_interval_sec"])
