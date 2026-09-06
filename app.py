import argparse
import json
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from ui.pet_window import PetWindow

ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Amadeus Presence desktop prototype")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-voice", action="store_true", help="Disable optional local voice pipeline")
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".local")
    args = parser.parse_args()

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Amadeus Presence")
    behavior = load_json(ROOT / "config" / "behavior.json")
    voice = {} if args.no_voice else load_json(ROOT / "config" / "voice.json")
    window = PetWindow(behavior, args.data_dir, args.debug, voice)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
