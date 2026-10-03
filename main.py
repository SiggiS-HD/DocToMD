"""Kommandozeilen-Einstiegspunkt für DocToMD."""

import sys

from app.cli import main


def _configure_utf8_streams() -> None:
    """Macht den maschinenlesbaren CLI-Strom unter Windows eindeutig UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


if __name__ == "__main__":
    _configure_utf8_streams()
    raise SystemExit(main())
