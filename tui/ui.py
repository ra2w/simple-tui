from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown as RichMarkdown

from .theme import INDIGO, GRAY

@dataclass
class Header:
    text: str


@dataclass
class Subheader:
    text: str


@dataclass
class Markdown:
    text: str


@dataclass
class Text:
    text: str


@dataclass
class TableEl:
    title: str
    rows: List[dict]
    columns: List[str] | None = None


def UI(*elements: Any) -> List[Any]:
    return [e for e in elements if e is not None]


def render_elements(console: Console, elements: Any | Iterable[Any] | None):
    if elements is None:
        return

    def iter_elems(obj):
        if obj is None:
            return
        # Strings are iterable but should be treated as a single element
        if isinstance(obj, str):
            yield obj
            return
        if isinstance(obj, (list, tuple)):
            for it in obj:
                yield it
            return
        # Generic iterable (e.g., generator)
        if hasattr(obj, "__iter__"):
            try:
                for it in obj:
                    yield it
                return
            except TypeError:
                pass
        # Fallback: single object
        yield obj

    for e in iter_elems(elements):
        if e is None:
            continue
        if isinstance(e, Header):
            console.print(f"[bold][{INDIGO}]{e.text}[/{INDIGO}][/bold]")
        elif isinstance(e, Subheader):
            console.print(f"[bold]{e.text}[/bold]")
        elif isinstance(e, Markdown):
            console.print(Panel.fit(RichMarkdown(e.text), border_style=INDIGO))
        elif isinstance(e, Text):
            console.print(e.text)
        elif isinstance(e, TableEl):
            cols = e.columns or (list(e.rows[0].keys()) if e.rows else [])
            t = Table(title=e.title, show_header=True, header_style=INDIGO)
            for c in cols:
                justify = "right" if c.lower() in {"id","count","value","amount","size","score","total"} else "left"
                style = "bold" if c == cols[0] else None
                t.add_column(c, justify=justify, style=style)
            for row in e.rows:
                t.add_row(*[str(row.get(c, "")) for c in cols])
            console.print(t)
        elif isinstance(e, str):
            # Auto-promote plain strings to Markdown panel for nicer formatting
            console.print(Panel.fit(e, border_style=INDIGO))
        elif isinstance(e, (list, tuple)) and e and all(isinstance(x, dict) for x in e):
            # Auto-render a list of dicts as a table (columns inferred)
            rows = list(e)
            cols = list(rows[0].keys()) if rows else []
            t = Table(title="", show_header=True, header_style=INDIGO)
            for c in cols:
                justify = "right" if c.lower() in {"id","count","value","amount","size","score","total"} else "left"
                style = "bold" if c == cols[0] else None
                t.add_column(c, justify=justify, style=style)
            for row in rows:
                t.add_row(*[str(row.get(c, "")) for c in cols])
            console.print(t)
        else:
            # Fallback: print string representation
            console.print(str(e))


def descriptors_to_elements(descs: Iterable[dict]) -> List[Any]:
    out: List[Any] = []
    for d in descs or []:
        try:
            k = d.get("k")
            if k == "md":
                out.append(Markdown(d.get("t", "")))
            elif k == "text":
                out.append(Text(d.get("t", "")))
            elif k == "table":
                out.append(TableEl(d.get("title", ""), d.get("rows", []), d.get("cols")))
            elif k == "header":
                out.append(Header(d.get("t", "")))
            elif k == "subheader":
                out.append(Subheader(d.get("t", "")))
        except Exception:
            # Skip malformed descriptors
            continue
    return out
