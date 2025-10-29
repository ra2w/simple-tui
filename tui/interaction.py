from __future__ import annotations
from typing import Any, Callable, Dict, Iterable, List, Optional

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML
except Exception:  # pragma: no cover
    PromptSession = None  # type: ignore
    HTML = None  # type: ignore


class Interaction:
    def ask_text(self, prompt: str, *, default: Optional[str] = None, multiline: bool = False) -> Optional[str]:
        raise NotImplementedError

    def choose(self, prompt: str, choices: List[str]) -> Optional[str]:
        raise NotImplementedError

    def multiselect(self, prompt: str, choices: List[str]) -> Optional[List[str]]:
        raise NotImplementedError

    def confirm(self, prompt: str, default: bool = False) -> Optional[bool]:
        raise NotImplementedError


class HeadlessInteraction(Interaction):
    """Interaction implementation for headless mode using pre-defined responses."""
    
    def __init__(self, responses: Dict[str, Any] = None, transcript: Optional[Any] = None):
        self.responses = responses or {}
        self.transcript = transcript
    
    def ask_text(self, prompt: str, *, default: Optional[str] = None, multiline: bool = False) -> Optional[str]:
        # Look for response by prompt key (simplified version of prompt)
        key = prompt.lower().replace(" ", "_").replace(":", "")

        # Try exact match first
        response = self.responses.get(prompt)
        if response is None:
            # Try simplified key
            response = self.responses.get(key)
        if response is None:
            # Try to extract argument name from prompt like "Enter name"
            words = prompt.lower().split()
            if "enter" in words and len(words) > 1:
                arg_name = words[-1]
                response = self.responses.get(arg_name)

        if response is not None:
            response = str(response)
            if self.transcript:
                self.transcript.record_prompt_response(prompt, response)
            return response

        # Use default if no response found
        if default is not None:
            if self.transcript:
                self.transcript.record_prompt_response(prompt, default)
            return default

        # No response and no default
        if self.transcript:
            self.transcript.record_output("err", f"No response configured for prompt: {prompt}")
        return None
    
    def choose(self, prompt: str, choices: List[str]) -> Optional[str]:
        response = self.ask_text(prompt)
        if response and response in choices:
            return response
        return None
    
    def multiselect(self, prompt: str, choices: List[str]) -> Optional[List[str]]:
        response = self.ask_text(prompt)
        if response is None:
            return None
        items = [x.strip() for x in response.split(',') if x.strip()]
        return [item for item in items if item in choices]
    
    def confirm(self, prompt: str, default: bool = False) -> Optional[bool]:
        response = self.ask_text(prompt)
        if response is None:
            return default
        return response.lower() in {'y', 'yes', 'true', '1'}


class TUIInteraction(Interaction):
    def __init__(self, session: Optional[PromptSession] = None):
        self._session = session or (PromptSession() if PromptSession else None)

    def ask_text(self, prompt: str, *, default: Optional[str] = None, multiline: bool = False) -> Optional[str]:
        if not self._session:
            return default
        try:
            prompt_kwargs = {
                "default": default or "",
                "multiline": multiline,
            }
            if multiline:
                prompt_kwargs["prompt_continuation"] = "... "
                toolbar = "Esc+Enter submit · Enter newline"
                if HTML:
                    prompt_kwargs["bottom_toolbar"] = HTML(
                        "<b>Esc+Enter</b> submit · Enter newline"
                    )
                else:
                    prompt_kwargs["bottom_toolbar"] = toolbar

            if HTML:
                return self._session.prompt(
                    HTML(f"<prompt>{prompt}</prompt> "),
                    **prompt_kwargs
                ).strip()
            return self._session.prompt(f"{prompt} ", **prompt_kwargs).strip()
        except (KeyboardInterrupt, EOFError):
            return None

    def choose(self, prompt: str, choices: List[str]) -> Optional[str]:
        # Minimal choice: just prompt with default shown; richer completer can be added later
        return self.ask_text(f"{prompt} ({'/'.join(choices)})")

    def multiselect(self, prompt: str, choices: List[str]) -> Optional[List[str]]:
        s = self.ask_text(f"{prompt} (comma-separated from {', '.join(choices)})")
        if s is None:
            return None
        items = [x.strip() for x in s.split(',') if x.strip()]
        return items

    def confirm(self, prompt: str, default: bool = False) -> Optional[bool]:
        d = 'Y/n' if default else 'y/N'
        s = self.ask_text(f"{prompt} [{d}]")
        if s is None or not s:
            return default
        return s.strip().lower() in {'y','yes'}
