"""Minimal YAML-frontmatter reader/writer (stdlib only).

Copied verbatim from the reference implementation. It parses the small subset of
YAML used in item files (`vault/items/<slug>.md`) without a third-party
dependency, so the engine can run from a thin shell. It is deliberately NOT a
full YAML parser — it covers scalars, flat lists, lists-of-dicts, and one level
of nested mappings, which is all an item file needs.

You should not need to touch this file when adapting the template.
"""
from __future__ import annotations

import ast
from typing import Any


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"null", "None", "~"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        try:
            return ast.literal_eval(value)
        except Exception:
            return value
    if value.startswith("{") and value.endswith("}"):
        try:
            return ast.literal_eval(value)
        except Exception:
            return value
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if value == "" or value.strip() != value or value.lower() in {"null", "true", "false"} or ":" in value:
            return repr(value)
        return value
    return repr(value)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    return parse_mapping(raw), body


def parse_mapping(raw: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith(" "):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            root[key] = parse_scalar(value)
            i += 1
            continue
        block, next_i = _parse_block(lines, i + 1, 2)
        root[key] = block
        i = next_i
    return root


def _parse_block(lines: list[str], start: int, indent: int) -> tuple[Any, int]:
    items: list[Any] = []
    mapping: dict[str, Any] = {}
    mode: str | None = None
    i = start
    prefix = " " * indent
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent < indent:
            break
        stripped = line[indent:]
        if stripped.startswith("- "):
            mode = "list"
            item_text = stripped[2:].strip()
            if item_text == "":
                item, i = _parse_block(lines, i + 1, indent + 2)
                items.append(item)
                continue
            if ":" in item_text and not item_text.startswith(("'", '"')):
                k, v = item_text.split(":", 1)
                item_dict: dict[str, Any] = {k.strip(): parse_scalar(v.strip()) if v.strip() else {}}
                i += 1
                while i < len(lines):
                    sub = lines[i]
                    if not sub.strip():
                        i += 1
                        continue
                    sub_indent = len(sub) - len(sub.lstrip(" "))
                    if sub_indent <= current_indent:
                        break
                    sub_text = sub.strip()
                    if ":" in sub_text:
                        sk, sv = sub_text.split(":", 1)
                        item_dict[sk.strip()] = parse_scalar(sv.strip()) if sv.strip() else {}
                    i += 1
                items.append(item_dict)
                continue
            items.append(parse_scalar(item_text))
            i += 1
            continue
        if line.startswith(prefix) and ":" in stripped:
            mode = mode or "dict"
            k, v = stripped.split(":", 1)
            mapping[k.strip()] = parse_scalar(v.strip()) if v.strip() else {}
        i += 1
    return (items if mode == "list" else mapping), i


def dumps_frontmatter(data: dict[str, Any], body: str) -> str:
    if not body.startswith("\n"):
        body = "\n" + body
    return "---\n" + dump_mapping(data).rstrip() + "\n---" + body


def dump_mapping(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            if value:
                lines.append(f"{prefix}{key}:")
                lines.append(dump_mapping(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {{}}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        item_items = list(item.items())
                        if not item_items:
                            lines.append(f"{prefix}  - {{}}")
                            continue
                        first_key, first_value = item_items[0]
                        lines.append(f"{prefix}  - {first_key}: {format_scalar(first_value)}")
                        for sub_key, sub_value in item_items[1:]:
                            lines.append(f"{prefix}    {sub_key}: {format_scalar(sub_value)}")
                    else:
                        lines.append(f"{prefix}  - {format_scalar(item)}")
        else:
            lines.append(f"{prefix}{key}: {format_scalar(value)}")
    return "\n".join(lines) + "\n"
