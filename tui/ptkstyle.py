from prompt_toolkit.styles import Style

style = Style.from_dict({
    "prompt": "#000000 bold",
    "command": "#87ff5f bold",
    "error": "#ff5f5f",
    "success": "#5fff5f",
    "info": "#8787af",
    "completion-menu": "bg:#262626 #d0d0d0",
    "completion-menu.completion": "bg:#262626 #a8a8a8",
    "completion-menu.completion.current": "bg:#444444 #ffffff bold",
    "completion-menu.meta.completion": "bg:#262626 #808080",
    "completion-menu.meta.completion.current": "bg:#444444 #d0d0d0",
})
