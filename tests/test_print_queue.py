from tui.app import App


def test_print_queue_drains_and_renders(tmp_path, capsys):
    app = App("queue_test", append_only=True)

    # Enqueue from a simulated command
    app.md("Hello")
    app.text("World")
    rows = [{"ID": 1, "Name": "X"}]
    app.table("Items", rows, columns=["ID", "Name"])

    # First render should print queued items, then clear the queue
    app._render()
    out = capsys.readouterr().out
    assert "Hello" in out and "World" in out and "Items" in out
    # Queue should be empty now
    assert not app.state.get("__print_queue__")
