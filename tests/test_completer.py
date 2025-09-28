from typing import Any, Dict

from tui.app import App, Arg
from tui import completers
from tui.commands import SlashCompleter


class DummyDoc:
    def __init__(self, text: str):
        self.text_before_cursor = text


def test_dataset_completion_for_delete(tmp_path):
    app = App("comp_test", append_only=True)
    app.state["items"] = [
        {"id": 1, "name": "Foo"},
        {"id": 2, "name": "Bar"},
    ]

    def fetch_names(ctx: Dict[str, Any]):
        return [i["name"] for i in ctx.get("state", {}).get("items", [])]

    @app.command("/delete", args=[Arg("name", str, completer=fetch_names)])
    def delete(name: str):
        pass

    comp = SlashCompleter(app.registry, history_store=app.history, state_provider=lambda: app.state)
    # After trailing space, should show both Foo and Bar
    items = list(comp.get_completions(DummyDoc("/delete "), None))
    texts = [c.text for c in items]
    assert "Foo" in texts and "Bar" in texts

    # With prefix 'F' should narrow to Foo
    items = list(comp.get_completions(DummyDoc("/delete F"), None))
    texts = [c.text for c in items]
    assert texts and all(t.startswith("F") for t in texts)


def test_dependent_completion(tmp_path):
    app = App("comp_dep", append_only=True)

    def fetch_projects(ctx: Dict[str, Any]):
        return ["alpha", "beta"]

    def fetch_tags(project: str, ctx: Dict[str, Any]):
        return {"alpha": ["core", "ml"], "beta": ["etl"]}.get(project, [])

    @app.command("/label", args=[
        Arg("project", str, completer=fetch_projects),
        Arg("tag", str, completer=completers.dependent("project", fetch_tags)),
    ])
    def label(project: str, tag: str):
        pass

    comp = SlashCompleter(app.registry, history_store=app.history, state_provider=lambda: app.state)

    # Complete project after space
    projs = list(comp.get_completions(DummyDoc("/label "), None))
    assert {c.text for c in projs} == {"alpha", "beta"}

    # After selecting project and a space, tag suggestions should depend on project
    tags = list(comp.get_completions(DummyDoc("/label alpha "), None))
    assert {c.text for c in tags} == {"core", "ml"}


def test_number_range_completion(tmp_path):
    app = App("comp_num", append_only=True)

    @app.command("/calc", args=[
        Arg("a", int, completer=completers.numbers(0, 10, 5)), 
        Arg("b", int, completer=completers.numbers(0, 10, 5))
    ])
    def calc(a: int, b: int):
        pass

    comp = SlashCompleter(app.registry, history_store=app.history, state_provider=lambda: app.state)

    # Completing first arg
    a_vals = list(comp.get_completions(DummyDoc("/calc "), None))
    assert {c.text for c in a_vals} == {"0", "5", "10"}

    # After entering first arg and a space, now completing b
    b_vals = list(comp.get_completions(DummyDoc("/calc 5 "), None))
    assert {c.text for c in b_vals} == {"0", "5", "10"}