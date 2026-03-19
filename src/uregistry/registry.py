"""
Directory-based configuration registry.

Reads and writes env vars from a directory tree where each file's path
becomes the variable name (parts joined with underscores, uppercased)
and file content becomes the value.

    env/AI/DEFAULT_MODEL  →  AI_DEFAULT_MODEL

Supports two layers: system (shared/global) and local (project-specific).
Local values take priority over system values. Writes always go to local.

No external dependencies.
"""

import os
import shlex
from pathlib import Path

DEFAULT_LOCAL_DIR = "env"
DEFAULT_SYSTEM_DIR: str | None = None


def _name_from_path(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return "_".join(part.upper() for part in rel.parts)


def _find_existing_path(root: Path, name: str) -> Path | None:
    """Find an existing file in a dir that maps to this var name."""
    if not root.exists():
        return None
    for path in root.rglob("*"):
        if path.is_file() and _name_from_path(root, path) == name:
            return path
    return None


def _relative_path_in(root: Path, name: str) -> Path | None:
    """Find the relative path for a var name within a root dir."""
    existing = _find_existing_path(root, name)
    if existing is not None:
        return existing.relative_to(root)
    return None


def _path_from_name(
    root: Path, name: str, system_root: Path | None = None
) -> Path:
    """Resolve var name to a file path, preferring existing files.

    Lookup order: root (local) first, then system_root.
    Use "/" to explicitly set directory boundaries:
        "AI/CRON_MODEL"  → env/AI/CRON_MODEL
        "A/B_C/D"        → env/A/B_C/D

    Without "/", existing files are matched first, then each "_" becomes "/".
    """
    if "/" in name:
        return root / name

    # Check local first
    existing = _find_existing_path(root, name)
    if existing is not None:
        return existing

    # Check system — reuse the same relative path in local
    if system_root is not None:
        rel = _relative_path_in(system_root, name)
        if rel is not None:
            return root / rel

    # Default: each underscore-separated part becomes a path component
    parts = name.split("_")
    return root.joinpath(*parts)


def _read_layer(root: Path) -> dict[str, str]:
    """Read all env vars from a single directory layer."""
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


def load_env(
    local_dir: str = DEFAULT_LOCAL_DIR,
    system_dir: str | None = DEFAULT_SYSTEM_DIR,
) -> dict[str, str]:
    """Load all env vars from system + local into os.environ.

    System vars are loaded first, then local overrides them.
    """
    merged: dict[str, str] = {}
    if system_dir:
        merged.update(_read_layer(Path(system_dir)))
    merged.update(_read_layer(Path(local_dir)))
    for name, value in merged.items():
        os.environ[name] = value
    return merged


def get_env(
    name: str,
    default: str | None = None,
    local_dir: str = DEFAULT_LOCAL_DIR,
    system_dir: str | None = DEFAULT_SYSTEM_DIR,
) -> str | None:
    """Read a single env var. Checks local first, then system."""
    local_root = Path(local_dir)
    path = _path_from_name(local_root, name)
    if path.is_file():
        return path.read_text().rstrip()

    if system_dir:
        system_root = Path(system_dir)
        sys_path = _path_from_name(system_root, name)
        if sys_path.is_file():
            return sys_path.read_text().rstrip()

    return default


def set_env(
    name: str,
    value: str,
    local_dir: str = DEFAULT_LOCAL_DIR,
    system_dir: str | None = DEFAULT_SYSTEM_DIR,
) -> None:
    """Write a single env var to local registry and update os.environ.

    If the var exists in system, the same relative path is used in local.
    """
    local_root = Path(local_dir)
    system_root = Path(system_dir) if system_dir else None
    path = _path_from_name(local_root, name, system_root=system_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n")
    env_name = _name_from_path(local_root, path)
    os.environ[env_name] = value


def delete_env(name: str, local_dir: str = DEFAULT_LOCAL_DIR) -> bool:
    """Delete an env var from local registry. Returns True if it existed.

    If the var also exists in system, it will become visible again.
    """
    root = Path(local_dir)
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


def list_env(
    local_dir: str = DEFAULT_LOCAL_DIR,
    system_dir: str | None = DEFAULT_SYSTEM_DIR,
) -> dict[str, str]:
    """List all env vars (system + local merged) without modifying os.environ."""
    merged: dict[str, str] = {}
    if system_dir:
        merged.update(_read_layer(Path(system_dir)))
    merged.update(_read_layer(Path(local_dir)))
    return merged


def _quote_fish(value: str) -> str:
    """Quote a value for fish shell (single quotes, escape existing ones)."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def dump_shell(
    local_dir: str = DEFAULT_LOCAL_DIR,
    system_dir: str | None = DEFAULT_SYSTEM_DIR,
    shell: str = "bash",
) -> str:
    """Return shell export statements for all env vars.

    shell: "bash" (also works for zsh/sh) or "fish"
    """
    lines = []
    env = sorted(list_env(local_dir, system_dir).items())
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
