from rich.console import Console
from .theme import GRAY

_console = Console()
def info(t): _console.print(f"[{GRAY}]{t}[/{GRAY}]")
def ok(t):   _console.print(f"[green]✓ {t}[/green]")
def warn(t): _console.print(f"[yellow]⚠ {t}[/yellow]")
def err(t):  _console.print(f"[red]Error: {t}[/red]")
