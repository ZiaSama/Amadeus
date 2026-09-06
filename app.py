import argparse
import json
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from ui.pet_window import PetWindow

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Amadeus Presence desktop prototype")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".local")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Amadeus Presence")
    config = json.loads((ROOT / "config" / "behavior.json").read_text(encoding="utf-8"))
    window = PetWindow(config, args.data_dir, args.debug)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
