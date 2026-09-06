from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterReply:
    text: str
    emotion: str = "neutral"
