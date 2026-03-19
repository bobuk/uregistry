"""
Directory-based configuration registry.

Reads and writes env vars from a directory tree where each file's path
becomes the variable name (parts joined with underscores, uppercased)
and file content becomes the value.

    env/AI/DEFAULT_MODEL  →  AI_DEFAULT_MODEL

No external dependencies.
"""

import os
import shlex
from pathlib import Path

DEFAULT_ENV_DIR = "env"


def _name_from_path(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return "_".join(part.upper() for part in rel.parts)


def _find_existing_path(root: Path, name: str) -> Path | None:
    """Find an existing file in the env dir that maps to this var name."""
    for path in root.rglob("*"):
        if path.is_file() and _name_from_path(root, path) == name:
            return path
    return None


def _path_from_name(root: Path, name: str) -> Path:
    """Resolve var name to a file path, preferring existing files.

    Use "/" to explicitly set directory boundaries:
        "AI/CRON_MODEL"  → env/AI/CRON_MODEL
        "A/B_C/D"        → env/A/B_C/D

    Without "/", existing files are matched first, then each "_" becomes "/".
    """
    if "/" in name:
        return root / name
    existing = _find_existing_path(root, name)
    if existing is not None:
        return existing
    # Default: each underscore-separated part becomes a path component
    parts = name.split("_")
    return root.joinpath(*parts)


def load_env(env_dir: str = DEFAULT_ENV_DIR) -> dict[str, str]:
    """Load all env vars from the directory tree into os.environ."""
    root = Path(env_dir)
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        name = _name_from_path(root, path)
        value = path.read_text().rstrip()
        result[name] = value
        os.environ[name] = value
    return result


def get_env(name: str, default: str | None = None, env_dir: str = DEFAULT_ENV_DIR) -> str | None:
    """Read a single env var from the directory (without loading all)."""
    root = Path(env_dir)
    path = _path_from_name(root, name)
    if path.is_file():
        return path.read_text().rstrip()
    return default


def set_env(name: str, value: str, env_dir: str = DEFAULT_ENV_DIR) -> None:
    """Write a single env var to the directory and update os.environ."""
    root = Path(env_dir)
    path = _path_from_name(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n")
    os.environ[name] = value


def delete_env(name: str, env_dir: str = DEFAULT_ENV_DIR) -> bool:
    """Delete an env var file. Returns True if it existed."""
    root = Path(env_dir)
    path = _path_from_name(root, name)
    if path.is_file():
        path.unlink()
        os.environ.pop(name, None)
        # Clean up empty parent dirs up to root
        parent = path.parent
        while parent != root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        return True
    return False


def list_env(env_dir: str = DEFAULT_ENV_DIR) -> dict[str, str]:
    """List all env vars from the directory without modifying os.environ."""
    root = Path(env_dir)
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        name = _name_from_path(root, path)
        value = path.read_text().rstrip()
        result[name] = value
    return result


def _quote_fish(value: str) -> str:
    """Quote a value for fish shell (single quotes, escape existing ones)."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def dump_shell(env_dir: str = DEFAULT_ENV_DIR, shell: str = "bash") -> str:
    """Return shell export statements for all env vars.

    shell: "bash" (also works for zsh/sh) or "fish"
    """
    lines = []
    env = sorted(list_env(env_dir).items())
    if shell == "fish":
        for name, value in env:
            lines.append(f"set -gx {name} {_quote_fish(value)}")
    else:
        for name, value in env:
            lines.append(f"export {name}={shlex.quote(value)}")
    return "\n".join(lines)


def _detect_shell() -> str:
    """Detect current shell from SHELL env var."""
    shell_path = os.environ.get("SHELL", "")
    if "fish" in shell_path:
        return "fish"
    return "bash"
