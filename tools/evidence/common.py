"""Shared helpers for evidence builders: git/env facts, pytest runner, hashing, tiny JSON-Schema validator."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "tools" / "evidence" / "schema.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def git_facts() -> dict:
    sha = _git("rev-parse", "HEAD") or "unknown"
    dirty = bool(_git("status", "--porcelain"))
    return {"git_sha": sha, "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"), "working_tree_dirty": dirty}


def run_pytest(target: str) -> dict:
    """Run pytest on one target in a subprocess and parse its summary line."""
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    summary = lines[-1].strip("= ") if lines else ""
    counts = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected)", summary)}
    return {"target": target, "command": "python -m pytest -q " + target, "exit_code": proc.returncode,
            "summary": summary, "passed": counts.get("passed", 0),
            "failed": counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)}


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def environment() -> dict:
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform()}


# ---- a deliberately small JSON-Schema validator (subset used by schema.json) -------------------

def _type_ok(value, t: str) -> bool:
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "null":
        return value is None
    raise ValueError(f"unsupported type in schema: {t}")


def validate(instance, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    """Return a list of error strings (empty = valid). Supports: $ref (#/$defs/..), type, enum, const,
    required, properties, additionalProperties (bool or schema), items, minItems, minLength, pattern, anyOf."""
    root = root if root is not None else schema
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            node = node[part]
        return validate(instance, node, root, path)
    errs: list[str] = []
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(instance, t) for t in types):
            return [f"{path}: expected {'|'.join(types)}, got {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in {schema['enum']}")
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: expected constant {schema['const']!r}, got {instance!r}")
    if "anyOf" in schema and not any(not validate(instance, s, root, path) for s in schema["anyOf"]):
        errs.append(f"{path}: matches none of anyOf")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errs.append(f"{path}: string shorter than {schema['minLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errs.append(f"{path}: {instance!r} does not match {schema['pattern']!r}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties", {})
        for key, val in instance.items():
            if key in props:
                errs += validate(val, props[key], root, f"{path}.{key}")
            else:
                ap = schema.get("additionalProperties", True)
                if ap is False:
                    errs.append(f"{path}: unexpected property {key!r}")
                elif isinstance(ap, dict):
                    errs += validate(val, ap, root, f"{path}.{key}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errs += validate(item, schema["items"], root, f"{path}[{i}]")
    return errs


def validate_packet(packet: dict) -> list[str]:
    return validate(packet, json.loads(SCHEMA_PATH.read_text()))
