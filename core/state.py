from dataclasses import dataclass


@dataclass
class WorldState:
    cursor_x: float = 0
    cursor_y: float = 0
    cursor_near: bool = False


@dataclass
class CharacterState:
    irritation: float = 0.05
    click_count: int = 0
    behavior: str = "idle"
    expression: str = "neutral"
    dragging: bool = False
    eye_x: float = 0
    eye_y: float = 0
    head_x: float = 0
    head_y: float = 0
    eye_open: float = 1
    voice_status: str = "idle"
    speech_text: str = ""
    last_event: str = "START"
    reason: str = "等待互动"
