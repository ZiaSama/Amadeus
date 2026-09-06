import json
from urllib import error, request

from brain.history import ConversationHistory
from brain.prompt import build_system_prompt
from brain.types import CharacterReply

_ALLOWED_EMOTIONS = {
    "neutral", "focused", "curious", "skeptical", "mild_annoyed",
    "annoyed", "confident", "embarrassed", "surprised", "tired", "concerned",
}

_SERVICE_PHRASES = (
    "有什么可以帮助你的吗",
    "有什么可以帮你的吗",
    "请问有什么需要",
    "很高兴为你服务",
    "我能为你做些什么",
)

_GREETING_INPUTS = {"你好", "您好", "嗨", "哈喽", "hello", "hi", "hey"}


class LocalLLM:
    """Small synchronous client for a local Ollama-compatible chat endpoint.

    The model is intentionally treated as a short-dialogue engine rather than a
    general-purpose assistant. Call this class only from a worker thread.
    """

    def __init__(self, config: dict, history: ConversationHistory | None = None):
        self.endpoint = config.get("endpoint", "http://127.0.0.1:11434/api/chat")
        self.model = config.get("model", "qwen2.5:1.5b")
        self.timeout_sec = float(config.get("timeout_sec", 30))
        self.temperature = float(config.get("temperature", 0.72))
        self.top_p = float(config.get("top_p", 0.90))
        self.num_predict = int(config.get("num_predict", 96))
        self.repeat_penalty = float(config.get("repeat_penalty", 1.08))
        self.keep_alive = config.get("keep_alive", "2m")
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
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_predict": self.num_predict,
                "repeat_penalty": self.repeat_penalty,
            },
        }).encode("utf-8")
        req = request.Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=self.timeout_sec) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"本地模型不可用：{exc}") from exc

        raw = body.get("message", {}).get("content", "").strip()
        result = self._parse_reply(raw)
        result = self._style_guard(text, result)
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

    @staticmethod
    def _style_guard(user_text: str, reply: CharacterReply) -> CharacterReply:
        """Remove a few high-frequency assistant clichés from very small models.

        This is deliberately narrow: the persona still comes from the prompt and
        model, while the guard only catches obvious customer-service regressions.
        """
        text = reply.text.strip()
        lowered_user = user_text.strip().lower().rstrip("!！?？。,.，")

        for phrase in _SERVICE_PHRASES:
            text = text.replace(phrase + "？", "").replace(phrase + "?", "").replace(phrase, "")
        text = " ".join(text.split()).strip(" ，,;；")

        if lowered_user in _GREETING_INPUTS and (not text or text in {"你好", "你好！", "您好", "您好！"}):
            return CharacterReply(text="……你好。突然这么正式干什么？", emotion="skeptical")

        if not text:
            text = "……嗯？"
        return CharacterReply(text=text, emotion=reply.emotion)
