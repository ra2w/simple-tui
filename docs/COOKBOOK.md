# TUI Cookbook

## Persisting Search Queries
```python
@app.command("/search", args=[Arg("query", str, history=True)])
def search(query):
    app.ok(f"Searching {query}")
```

## Custom Completers
```python
from tui.app import App, Arg
from tui import completers

app = App("example")

# Simple function completer
def get_projects(ctx): 
    return ["alpha", "beta", "gamma"]

# Dependent completer
def get_tags(project, ctx): 
    return ["core", "infra", "tooling"] if project else []

@app.command("/label", args=[
    Arg("project", completer=get_projects),
    Arg("tag", completer=completers.dependent("project", get_tags))
])
def label(project, tag):
    app.ok(f"Labeled {project} with {tag}")
```

## Path Completion
```python
from tui.app import Path

@app.command("/open", args=[Arg("path", type=Path)])
def open_file(path):
    app.ok(f"Opening {path}")
```