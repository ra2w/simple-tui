from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from prompt_toolkit.completion import Completer, Completion

from .messages import err


Handler = Callable[[List[str]], None]


@dataclass
class ParamPlan:
    name: str
    flag: Optional[str]
    convert: Callable[[str], Any]
    default: Any
    required: bool
    repeat: bool
    prompt: bool
    multiline: bool
    definition: Any

    def runtime(self) -> Dict[str, Any]:
        return {
            "plan": self,
            "name": self.name,
            "flag": self.flag,
            "convert": self.convert,
            "default": self.default,
            "required": self.required,
            "provided": False,
            "repeat": self.repeat,
            "prompt": self.prompt,
            "multiline": self.multiline,
            "definition": self.definition,
        }


@dataclass
class CommandSpec:
    name: str
    args: List[Any]
    params: List[ParamPlan]

    @classmethod
    def from_args(
        cls,
        name: str,
        args: Sequence[Any],
        converter_for: Callable[[type], Callable[[str], Any]],
        optional_types: Sequence[type] = (),
    ) -> "CommandSpec":
        requireds: List[Any] = []
        optionals: List[Any] = []
        optional_types_tuple = tuple(optional_types) if optional_types else ()
        for arg in args:
            if optional_types_tuple and isinstance(arg, optional_types_tuple):
                optionals.append(arg)
            elif getattr(arg, "default", None) is not None:
                optionals.append(arg)
            else:
                requireds.append(arg)

        plans: List[ParamPlan] = []

        for a in requireds:
            plans.append(
                ParamPlan(
                    name=a.name,
                    flag=None,
                    convert=converter_for(getattr(a, "type", str)),
                    default=None,
                    required=True,
                    repeat=bool(getattr(a, "repeat", False)),
                    prompt=bool(getattr(a, "prompt", False)),
                    multiline=bool(getattr(a, "multiline", False)),
                    definition=a,
                )
            )

        for o in optionals:
            plans.append(
                ParamPlan(
                    name=o.name,
                    flag=f"--{o.name}",
                    convert=converter_for(getattr(o, "type", str)),
                    default=getattr(o, "default", None),
                    required=False,
                    repeat=bool(getattr(o, "repeat", False)),
                    prompt=bool(getattr(o, "prompt", False)),
                    multiline=bool(getattr(o, "multiline", False)),
                    definition=o,
                )
            )

        return cls(name=name, args=list(args), params=plans)

    def runtime_plan(self) -> List[Dict[str, Any]]:
        return [
            {
                **plan.runtime(),
                "value": [] if plan.repeat else None,
            }
            for plan in self.params
        ]

    def completion_plan(self) -> List[Dict[str, Any]]:
        return [
            {
                "plan": plan,
                "name": plan.name,
                "flag": plan.flag,
                "repeat": plan.repeat,
                "provided": False,
            }
            for plan in self.params
        ]

    def history_entries(self, values: Dict[str, Any]) -> Iterable[tuple[str, Any]]:
        for plan in self.params:
            definition = plan.definition
            if getattr(definition, "history", False):
                val = values.get(plan.name)
                if val is not None:
                    yield plan.name, val

    def parse(
        self,
        argv: Sequence[str],
        *,
        on_error: Callable[[str], None],
        prompt_fn: Optional[Callable[[ParamPlan, Optional[str]], Optional[str]]] = None,
        interactive: bool = False,
    ) -> Optional[Dict[str, Any]]:
        runtime = self.runtime_plan()
        values: Dict[str, Any] = {}
        plan_by_flag = {
            entry["flag"]: entry for entry in runtime if entry.get("flag")
        }

        for entry in runtime:
            plan = entry["plan"]
            if not entry["required"]:
                if plan.repeat:
                    default_val = entry["default"]
                    if default_val is None:
                        values[entry["name"]] = []
                        entry["value"] = []
                    elif isinstance(default_val, list):
                        values[entry["name"]] = list(default_val)
                        entry["value"] = list(default_val)
                    else:
                        values[entry["name"]] = [default_val]
                        entry["value"] = [default_val]
                else:
                    values[entry["name"]] = entry["default"]
                    entry["value"] = entry["default"]

        def next_pos_index(start: int = 0) -> int:
            j = start
            while j < len(runtime) and runtime[j]["provided"]:
                j += 1
            return j

        pos_cursor = next_pos_index(0)
        i = 0
        while i < len(argv):
            tok = argv[i]
            if tok.startswith("--"):
                key, eq, val = tok.partition("=")
                entry = plan_by_flag.get(key)
                if not entry:
                    on_error(f"Unknown option: {key}")
                    return None
                if eq:
                    raw = val
                else:
                    if i + 1 >= len(argv):
                        on_error(f"Option {key} requires a value")
                        return None
                    raw = argv[i + 1]
                    i += 1
                try:
                    converted = entry["convert"](raw)
                    if entry["repeat"]:
                        values.setdefault(entry["name"], []).append(converted)
                        entry.setdefault("value", []).append(converted)
                    else:
                        values[entry["name"]] = converted
                        entry["value"] = converted
                    entry["provided"] = True
                except Exception:
                    on_error(f"Invalid value for {key}")
                    return None
            else:
                pos_cursor = next_pos_index(pos_cursor)
                if pos_cursor >= len(runtime):
                    on_error("Too many positional arguments")
                    return None
                entry = runtime[pos_cursor]
                raw_tok = tok
                if entry["multiline"] and not entry["repeat"]:
                    raw_chunks = argv[i:]
                    raw_tok = " ".join(raw_chunks)
                    i = len(argv)
                try:
                    converted = entry["convert"](raw_tok)
                    if entry["repeat"]:
                        values.setdefault(entry["name"], []).append(converted)
                        entry.setdefault("value", []).append(converted)
                    else:
                        values[entry["name"]] = converted
                        entry["value"] = converted
                    entry["provided"] = True
                except Exception:
                    on_error(f"Invalid value for {entry['name']}")
                    return None
                if not entry["repeat"]:
                    pos_cursor += 1
            i += 1

        missing_required = [
            entry["name"] for entry in runtime if entry["required"] and not entry["provided"]
        ]
        needs_prompt = [
            entry
            for entry in runtime
            if entry["prompt"]
            and (
                not entry["provided"]
                or (interactive and entry["multiline"])
            )
        ]

        if (missing_required or needs_prompt) and interactive and prompt_fn:
            to_prompt = []
            for entry in runtime:
                should_prompt = False
                if (entry["required"] or entry["prompt"]) and not entry["provided"]:
                    should_prompt = True
                elif entry["prompt"] and entry["multiline"]:
                    should_prompt = True
                if should_prompt:
                    to_prompt.append(entry)
            for entry in to_prompt:
                plan = entry["plan"]
                definition = plan.definition
                default_attr = getattr(definition, "default", None)
                default_text = None
                entry_value = entry.get("value")
                if entry_value not in (None, [], {}):
                    if plan.repeat:
                        default_text = ", ".join(str(v) for v in entry_value)
                    else:
                        default_text = str(entry_value)
                elif default_attr not in (None, [], {}):
                    default_text = str(default_attr)
                ans = prompt_fn(plan, default_text)
                if ans is None:
                    on_error("Canceled")
                    return None
                if not ans and not entry["required"]:
                    entry["provided"] = True
                    entry["value"] = entry_value
                    continue
                try:
                    if plan.repeat:
                        raw_items = [x.strip() for x in ans.split(',') if x.strip()]
                        converted_items = [plan.convert(item) for item in raw_items]
                        if not converted_items and entry["required"]:
                            on_error(f"Missing: {plan.name}")
                            return None
                        if converted_items:
                            values[plan.name] = converted_items
                            entry["value"] = list(converted_items)
                    else:
                        values[plan.name] = plan.convert(ans)
                        entry["value"] = values[plan.name]
                    entry["provided"] = True
                except Exception:
                    on_error(f"Invalid value for {plan.name}")
                    return None
            missing_required = [
                entry["name"]
                for entry in runtime
                if entry["required"] and not entry["provided"]
            ]
            if missing_required:
                on_error(f"Missing: {' '.join(missing_required)}")
                return None
        elif missing_required:
            on_error(f"Missing: {' '.join(missing_required)}")
            return None

        return values


@dataclass
class CommandEntry:
    handler: Handler
    help_text: str
    spec: CommandSpec


class CommandRegistry:
    def __init__(self):
        self._handlers: Dict[str, CommandEntry] = {}

    def register(self, name: str, fn: Handler, help_text: str, spec: CommandSpec):
        self._handlers[name] = CommandEntry(fn, help_text, spec)

    def items(self):
        return self._handlers.items()

    def resolve(self, name: str) -> Optional[CommandEntry]:
        return self._handlers.get(name)

    def get_args(self, name: str) -> List[Any]:
        entry = self._handlers.get(name)
        return entry.spec.args if entry else []


class SlashCompleter(Completer):
    def __init__(self, registry, history_store=None, state_provider=None):
        self.registry = registry
        self.history_store = history_store
        self.state_provider = state_provider or (lambda: {})

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        s = text.lstrip()
        if not s.startswith('/'):
            return
        has_trailing_space = s.endswith(' ')

        tokens = s.split()
        if not tokens:
            return

        if len(tokens) == 1 and not has_trailing_space:
            for name, entry in self.registry.items():
                if name.startswith(tokens[0]):
                    display = f"{name} — {entry.help_text}"
                    yield Completion(
                        name,
                        start_position=-len(tokens[0]),
                        display=display,
                        display_meta="command",
                    )
            return

        cmd = tokens[0]
        entry = self.registry.resolve(cmd)
        if not entry:
            return
        spec = entry.spec
        if not spec.params:
            return

        plan_entries = spec.completion_plan()
        plan_by_flag = {
            p["flag"]: p for p in plan_entries if p.get("flag")
        }

        def next_pos_index(start: int = 0) -> int:
            j = start
            while j < len(plan_entries) and plan_entries[j]["provided"]:
                j += 1
            return j

        args_tokens = tokens[1:]
        if has_trailing_space:
            args_tokens.append("")

        active_token = args_tokens[-1] if args_tokens else ""
        completion_prefix = "" if has_trailing_space else active_token
        replacement_len = len(completion_prefix)
        if completion_prefix.startswith("--") and "=" in completion_prefix:
            completion_prefix = completion_prefix.split("=", 1)[1]
            replacement_len = len(completion_prefix)

        parsed_values: Dict[str, Any] = {}
        tokens_for_parse = list(args_tokens)
        if has_trailing_space and tokens_for_parse:
            tokens_for_parse = tokens_for_parse[:-1]

        pos_cursor = next_pos_index(0)
        i = 0
        last_entry = None
        while i < len(tokens_for_parse):
            tok = tokens_for_parse[i]
            if tok.startswith("--"):
                key, eq, val = tok.partition("=")
                entry_plan = plan_by_flag.get(key)
                if not entry_plan:
                    i += 1
                    continue
                if eq:
                    raw = val
                else:
                    if i + 1 >= len(tokens_for_parse):
                        break
                    raw = tokens_for_parse[i + 1]
                    i += 1
                plan_def = entry_plan["plan"]
                if plan_def.repeat:
                    parsed_values.setdefault(plan_def.name, []).append(raw)
                else:
                    parsed_values[plan_def.name] = raw
                entry_plan["provided"] = True
                last_entry = entry_plan
            else:
                pos_cursor = next_pos_index(pos_cursor)
                if pos_cursor >= len(plan_entries):
                    break
                entry_plan = plan_entries[pos_cursor]
                plan_def = entry_plan["plan"]
                if plan_def.repeat:
                    parsed_values.setdefault(plan_def.name, []).append(tok)
                else:
                    parsed_values[plan_def.name] = tok
                entry_plan["provided"] = True
                last_entry = entry_plan
                if not plan_def.repeat:
                    pos_cursor += 1
            i += 1

        active_plan = None
        if has_trailing_space:
            pos_idx = next_pos_index(0)
            if pos_idx < len(plan_entries):
                active_plan = plan_entries[pos_idx]["plan"]
        elif active_token.startswith("--"):
            flag_name = active_token.split("=", 1)[0]
            entry_plan = plan_by_flag.get(flag_name)
            if entry_plan:
                active_plan = entry_plan["plan"]
        elif last_entry is not None:
            active_plan = last_entry["plan"]
        else:
            pos_idx = next_pos_index(0)
            if pos_idx < len(plan_entries):
                active_plan = plan_entries[pos_idx]["plan"]

        if not active_plan:
            return
        active_arg = getattr(active_plan, "definition", None)
        if not active_arg or not hasattr(active_arg, "get_completer"):
            return

        completer_fn = active_arg.get_completer()
        if not completer_fn:
            return

        context = {
            "prefix": completion_prefix,
            "command": cmd,
            "arg_name": active_plan.name,
            "tokens": tokens,
            "state": self.state_provider(),
            "history": self.history_store,
            "arg_values": parsed_values,
        }

        suggestions = completer_fn(context)
        for suggestion in suggestions:
            if (
                completion_prefix
                and not (active_token.startswith("--") and "=" not in active_token)
                and not suggestion.startswith(completion_prefix)
            ):
                continue
            yield Completion(
                suggestion,
                start_position=-replacement_len,
                display=suggestion,
                display_meta="value",
            )


def dispatch(registry: CommandRegistry, cmd: str, *, on_error=None):
    try:
        parts: List[str] = shlex.split(cmd.strip())
    except ValueError as exc:
        handler = on_error or err
        handler(f"Parse error: {exc}")
        return
    if not parts:
        return
    name, args = parts[0], parts[1:]
    entry = registry.resolve(name)
    if not entry and not name.startswith('/'):
        entry = registry.resolve('/' + name)
    if not entry:
        handler = on_error or err
        handler(f"Unknown: {name}")
        return
    entry.handler(args)
