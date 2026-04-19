from __future__ import annotations

from rich.console import Console


class SafeLogger:
    def __init__(self, privacy_safe_logging: bool = True) -> None:
        self.console = Console()
        self.privacy_safe_logging = privacy_safe_logging

    def info(self, message: str) -> None:
        self.console.print(f"[cyan][info][/cyan] {message}")

    def warn(self, message: str) -> None:
        self.console.print(f"[yellow][warn][/yellow] {message}")

    def error(self, message: str) -> None:
        self.console.print(f"[red][error][/red] {message}")

    def success(self, message: str) -> None:
        self.console.print(f"[green][ok][/green] {message}")

    def safe_detail(self, message: str) -> None:
        if self.privacy_safe_logging:
            self.console.print(message)
