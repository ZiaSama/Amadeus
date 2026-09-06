from collections import deque


class ConversationHistory:
    def __init__(self, max_turns: int = 8):
        self._turns = deque(maxlen=max_turns * 2)

    def add_user(self, text: str) -> None:
        self._turns.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._turns.append({"role": "assistant", "content": text})

    def messages(self) -> list[dict[str, str]]:
        return list(self._turns)
