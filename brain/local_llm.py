import json
from urllib import error, request

from brain.history import ConversationHistory
from brain.prompt import build_system_prompt
from brain.types import CharacterReply

_ALLOWED_EMOTIONS = {
    "neutral", "focused", "curious", "skeptical", "mild_annoyed",
    "annoyed", "confident", "embarrassed", "surprised", "tired", "concerned",
}


class LocalLLM:
    """Small synchronous client for a local Ollama-compatible chat endpoint.

    This class intentionally has no third-party dependency. Call it from a worker
    thread; network access is localhost only unless the config is changed.
    """

    def __init__(self, config: dict, history: ConversationHistory | None = None):
        self.endpoint = config.get("endpoint", "http://127.0.0.1:11434/api/chat")
        self.model = config.get("model", "qwen2.5:1.5b")
        self.timeout_sec = float(config.get("timeout_sec", 30))
        self.history = history or ConversationHistory(int(config.get("history_turns", 8)))

    def reply(self, text: str, irritation: float = 0.0, behavior: str = "idle") -> CharacterReply:
        messages = [{"role": "system", "content": build_system_prompt(irritation, behavior)}]
        messages.extend(self.history.messages())
        messages.append({"role": "user", "content": text})
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.65},
        }).encode("utf-8")
        req = request.Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=self.timeout_sec) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"本地模型不可用：{exc}") from exc

        raw = body.get("message", {}).get("content", "").strip()
        result = self._parse_reply(raw)
        self.history.add_user(text)
        self.history.add_assistant(result.text)
        return result

    @staticmethod
    def _parse_reply(raw: str) -> CharacterReply:
        candidate = raw.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3:
                candidate = "\n".join(lines[1:-1]).strip()
                if candidate.lower().startswith("json\n"):
                    candidate = candidate[5:].strip()
        try:
            data = json.loads(candidate)
            text = str(data.get("text", "")).strip()
            emotion = str(data.get("emotion", "neutral")).strip()
            if not text:
                raise ValueError("empty text")
            if emotion not in _ALLOWED_EMOTIONS:
                emotion = "neutral"
            return CharacterReply(text=text, emotion=emotion)
        except (json.JSONDecodeError, TypeError, ValueError):
            cleaned = raw.strip() or "……嗯？"
            return CharacterReply(text=cleaned, emotion="neutral")
