from __future__ import annotations
from pathlib import Path as SysPath
from typing import Dict, Any

from pathlib import Path as FSPath
from tui.app import App, Arg, Opt, Path
from tui import completers


# Demo datasets for dependent completion
PROJECT_TAGS: Dict[str, list[str]] = {
    "alpha": ["core", "infra", "ml"],
    "beta": ["etl", "batch"],
    "gamma": ["viz", "ui"],
    "delta": ["ops", "cost"],
}


def main():
    app = App(
        "tui_showcase_v3",
        title="🎛️ TUI Showcase (v3)",
        append_only=True,
        interactive_prompts=True,
    )

    # Initial state
    app.state.setdefault("items", [])  # [{id, name, desc}]
    app.state.setdefault("notes", [])  # [{title, body}]
    app.state.setdefault("color", "indigo")

    @app.on_start
    def show_intro(app_instance: App):
        app_instance.markdown(
            "Type '/' for commands. Try /help to explore features."
        )
        app_instance.write(
            "Multi-line prompt demo: run /note and submit with Esc+Enter."
        )
        app_instance.write(f"Current color: {app_instance.state.get('color', 'indigo')}")
        items = app_instance.state.get("items", [])
        notes = app_instance.state.get("notes", [])
        if not items:
            app_instance.info("No items yet. Use /add to create one!")
        else:
            rows = [
                {"ID": it["id"], "Name": it["name"], "Description": it["description"]}
                for it in items
            ]
            app_instance.table("Items", rows, columns=["ID", "Name", "Description"])
        if notes:
            note_rows = [
                {"Title": it["title"], "Body": it["body"].splitlines()[0][:40]}
                for it in notes
            ]
            app_instance.table("Notes", note_rows, columns=["Title", "Body"])

    # --- Commands demonstrating providers and typed args ---

    @app.command(
        "/add",
        args=[Arg("name", str, history=True, prompt=True), Opt("description", str, default="No description")],
    )
    def add(name: str, description: str = "No description"):
        """Add a new item with an optional description"""
        items = app.state["items"]
        if any(i["name"] == name for i in items):
            app.err(f"Item '{name}' already exists!"); return
        items.append({"id": len(items) + 1, "name": name, "description": description})
        app.ok(f"Added '{name}'")


    @app.command("/list", args=[])
    def list():
        """List all items"""
        items = app.state["items"]
        rows = [
            {"ID": it["id"], "Name": it["name"], "Description": it["description"]}
            for it in items
        ]
        app.table("Items", rows, columns=["ID", "Name", "Description"])


    @app.command("/set",args=[Arg("name", str, completer=lambda ctx: [i["name"] for i in ctx.get("state", {}).get("items", [])], prompt=True),
    Arg("description", str, prompt=True),   
    ])
    def set(name: str, description: str):
        """Set the description of an existing item"""
        items = app.state["items"]
        for item in items:
            if item["name"] == name:
                item["description"] = description
                app.ok(f"Set description of '{name}' to '{description}'")
                return
        app.err(f"Item '{name}' not found!")

    @app.command(
        "/delete",
        args=[Arg("name", str, completer=lambda ctx: [i["name"] for i in ctx.get("state", {}).get("items", [])], prompt=True)],
    )
    def delete(name: str):
        """Delete an existing item by name (live completions)"""
        items = app.state["items"]
        filtered = [i for i in items if i["name"] != name]
        if len(filtered) == len(items):
            app.err(f"Item '{name}' not found!"); return
        items[:] = filtered
        app.ok(f"Deleted '{name}'")

    # History + number-range
    @app.command(
        "/search",
        args=[Arg("query", str, history=True, prompt=True), Opt("limit", int, default=20, completer=completers.numbers(10, 100, 10))],
    )
    def search(query: str, limit: int = 20):
        """Search using history-backed query and optional limit"""
        app.ok(f"Searching '{query}' (limit={limit})")

    # Path completion
    @app.command("/open", args=[Arg("path", Path)])
    def open_path(path: FSPath):
        """Open a filesystem path (demo of path completion)"""
        try:
            content = path.read_text()
        except OSError as exc:
            app.err(f"Could not read {path}: {exc}")
            return
        app.markdown(content)
        app.ok(f"Opened: {path}")

    # Enum
    @app.command("/color", args=[Arg("color", str, completer=completers.choices("red", "green", "blue", "indigo"))])
    def set_color(color: str):
        """Set current color (enum completion)"""
        app.state["color"] = color
        app.ok(f"Color set to: {color}")
        app.write(f"Current color: {color}")
        items = app.state.get("items", [])
        if items:
            rows = [
                {"ID": it["id"], "Name": it["name"], "Description": it["description"]}
                for it in items
            ]
            app.table("Items", rows, columns=["ID", "Name", "Description"])
        else:
            app.info("No items yet. Use /add to create one!")

    # Number range for quick math
    @app.command(
        "/calc",
        args=[Arg("a", int, completer=completers.numbers(0, 50, 5)), Arg("b", int, completer=completers.numbers(0, 50, 5))],
    )
    def calc(a: int, b: int):
        """Add two numbers with number-range suggestions"""
        app.ok(f"calc: {a} + {b} = {a + b}")

    @app.command(
        "/note",
        args=[
            Arg("title", str, prompt=True, history=True),
            Arg("body", str, prompt=True, multiline=True),
        ],
    )
    def note(title: str, body: str):
        """Capture a multi-line note (submit prompt with Esc+Enter)"""
        notes = app.state.setdefault("notes", [])
        notes[:] = [n for n in notes if n["title"] != title]
        notes.append({"title": title, "body": body})
        app.ok(f"Saved note '{title}' with {len(body.splitlines())} line(s)")
        app.markdown(f"### {title}\n{body}")

    # Dataset + Dependent
    def fetch_projects(ctx: Dict[str, Any]):
        return sorted(PROJECT_TAGS.keys())

    def fetch_tags(project: str, ctx: Dict[str, Any]):
        return PROJECT_TAGS.get(project, ["general"]) if project else []

    @app.command(
        "/label",
        args=[
            Arg("project", str, completer=lambda ctx: sorted(PROJECT_TAGS.keys())),
            Arg("tag", str, completer=completers.dependent("project", fetch_tags)),
        ],
    )
    def label(project: str, tag: str):
        """Choose project then tag (dependent completion)"""
        app.ok(f"Labeling project '{project}' with tag '{tag}'")

    # Help & man pages
    @app.command("/help", args=[])
    def show_help():
        """List available commands with one-line help"""
        lines = ["Available commands:"]
        for name, (_, help_text, _) in sorted(app.registry.items(), key=lambda x: x[0]):
            lines.append(f"  {name} — {help_text}")
        lines.append("  /help — List commands")
        app.ok("\n".join(lines))

    app.run()


if __name__ == "__main__":
    main()
