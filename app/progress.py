"""Stabile Fortschrittsereignisse für CLI und externe Aufrufer."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import sys
from time import perf_counter_ns
from typing import Callable, TextIO


ProgressCallback = Callable[[str, str, str], None]


@dataclass(slots=True)
class ProgressReporter:
    """Schreibt Fortschritt getrennt vom finalen CLI-Ergebnis auf stderr."""

    mode: str
    stream: TextIO = field(default_factory=lambda: sys.stderr)
    _started_ns: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.mode not in {"none", "human", "jsonl"}:
            raise ValueError("progress mode muss none, human oder jsonl sein.")
        self._started_ns = perf_counter_ns()

    def __call__(self, phase: str, status: str, message: str) -> None:
        if self.mode == "none":
            return
        elapsed_ms = (perf_counter_ns() - self._started_ns) // 1_000_000
        if self.mode == "human":
            print(f"[{elapsed_ms / 1000:.1f}s] {message}", file=self.stream, flush=True)
            return
        print(json.dumps({"schema_version": "1.0", "event": "progress", "phase": phase, "status": status, "message": message, "elapsed_ms": elapsed_ms}, ensure_ascii=False), file=self.stream, flush=True)


__all__ = ["ProgressCallback", "ProgressReporter"]
