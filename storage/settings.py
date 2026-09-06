import json
from pathlib import Path


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    result = {}
    for key in ("x", "y"):
        if type(data.get(key)) is int:
            result[key] = data[key]
    if type(data.get("always_on_top")) is bool:
        result["always_on_top"] = data["always_on_top"]
    return result


def save_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    temporary.replace(path)
