"""Simple function-based completers for command arguments."""
from __future__ import annotations
from typing import List, Callable, Any, Dict
from pathlib import Path


def choices(*items: str) -> Callable[[Dict[str, Any]], List[str]]:
    """Complete from a fixed list of choices."""
    return lambda ctx: [item for item in items if item.startswith(ctx.get("prefix", ""))]




def paths(extensions: List[str] = None) -> Callable[[Dict[str, Any]], List[str]]:
    """Complete file paths, optionally filtered by extensions."""
    def completer(ctx: Dict[str, Any]) -> List[str]:
        prefix = ctx.get("prefix", "")
        base_path = Path(prefix or ".")
        
        if base_path.is_dir():
            parent = base_path
            prefix_to_match = ""
        else:
            parent = base_path.parent
            prefix_to_match = base_path.name
        
        results = []
        try:
            for path in parent.iterdir():
                name = path.name
                if name.startswith(prefix_to_match):
                    # Add trailing slash for directories
                    display = str(path) + ("/" if path.is_dir() else "")
                    
                    # Filter by extensions if provided
                    if extensions and path.is_file():
                        if not any(name.endswith(ext) for ext in extensions):
                            continue
                    
                    results.append(display)
        except (OSError, PermissionError):
            pass
        
        return sorted(results)
    return completer


def history(limit: int = 10) -> Callable[[Dict[str, Any]], List[str]]:
    """Complete from command history."""
    def completer(ctx: Dict[str, Any]) -> List[str]:
        prefix = ctx.get("prefix", "")
        command = ctx.get("command", "")
        arg_name = ctx.get("arg_name", "")
        history_store = ctx.get("history")
        
        if not history_store:
            return []
        
        # Get history items for this command/arg combination
        items = history_store.get(command, arg_name, limit)
        return [item for item in items if item.startswith(prefix)]
    return completer


def numbers(start: int = 0, stop: int = 100, step: int = 10) -> Callable[[Dict[str, Any]], List[str]]:
    """Complete with numeric values in a range."""
    def completer(ctx: Dict[str, Any]) -> List[str]:
        prefix = ctx.get("prefix", "")
        results = []
        for n in range(start, stop + 1, step):
            s = str(n)
            if s.startswith(prefix):
                results.append(s)
        return results
    return completer


def dependent(parent_arg: str, fetch: Callable[[str, Dict[str, Any]], List[str]]) -> Callable[[Dict[str, Any]], List[str]]:
    """Complete based on the value of another argument."""
    def completer(ctx: Dict[str, Any]) -> List[str]:
        prefix = ctx.get("prefix", "")
        arg_values = ctx.get("arg_values") or {}
        parent_value: Any = arg_values.get(parent_arg, "")
        if isinstance(parent_value, list):
            parent_value = parent_value[-1] if parent_value else ""
        if parent_value is None:
            parent_value = ""

        # Get dependent values
        items = fetch(parent_value, ctx)
        return [item for item in items if item.startswith(prefix)]
    return completer


# Convenience functions for common cases
none = lambda ctx: []  # No completion
any_string = lambda ctx: []  # Accept any string without suggestions
