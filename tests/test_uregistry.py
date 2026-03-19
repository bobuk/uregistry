import os
from pathlib import Path

import pytest

from uregistry import (
    delete_env,
    dump_shell,
    get_env,
    list_env,
    load_env,
    set_env,
)
from uregistry.registry import (
    _detect_shell,
    _find_existing_path,
    _name_from_path,
    _path_from_name,
    _quote_fish,
    _read_layer,
)


def _write(path: Path, content: str = "val\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# --- _name_from_path ---


def test_name_from_path_single_file(tmp_path):
    assert _name_from_path(tmp_path, tmp_path / "TOKEN") == "TOKEN"


def test_name_from_path_nested(tmp_path):
    assert _name_from_path(tmp_path, tmp_path / "AI" / "DEFAULT_MODEL") == "AI_DEFAULT_MODEL"


def test_name_from_path_deep(tmp_path):
    assert _name_from_path(tmp_path, tmp_path / "a" / "b" / "c") == "A_B_C"


# --- _find_existing_path ---


def test_find_existing_path_found(tmp_path):
    f = tmp_path / "AI" / "MODEL"
    _write(f)
    assert _find_existing_path(tmp_path, "AI_MODEL") == f


def test_find_existing_path_not_found(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    assert _find_existing_path(tmp_path, "MISSING") is None


def test_find_existing_path_missing_dir(tmp_path):
    assert _find_existing_path(tmp_path / "nonexistent", "X") is None


# --- _path_from_name ---


def test_path_from_name_with_slash(tmp_path):
    assert _path_from_name(tmp_path, "AI/CRON_MODEL") == tmp_path / "AI" / "CRON_MODEL"


def test_path_from_name_existing_file(tmp_path):
    f = tmp_path / "AI" / "DEFAULT_MODEL"
    _write(f)
    assert _path_from_name(tmp_path, "AI_DEFAULT_MODEL") == f


def test_path_from_name_no_existing(tmp_path):
    assert _path_from_name(tmp_path, "A_B_C") == tmp_path / "A" / "B" / "C"


def test_path_from_name_uses_system_path(tmp_path):
    """When var exists in system but not local, reuse system's relative path."""
    local = tmp_path / "local"
    system = tmp_path / "system"
    local.mkdir()
    _write(system / "AI" / "DEFAULT_MODEL", "sys\n")

    result = _path_from_name(local, "AI_DEFAULT_MODEL", system_root=system)
    assert result == local / "AI" / "DEFAULT_MODEL"


def test_path_from_name_local_wins_over_system(tmp_path):
    """When var exists in both, local path is used."""
    local = tmp_path / "local"
    system = tmp_path / "system"
    _write(local / "AI" / "DEFAULT_MODEL", "loc\n")
    _write(system / "AI" / "DEFAULT_MODEL", "sys\n")

    result = _path_from_name(local, "AI_DEFAULT_MODEL", system_root=system)
    assert result == local / "AI" / "DEFAULT_MODEL"


# --- _read_layer ---


def test_read_layer(tmp_path):
    _write(tmp_path / "X", "1\n")
    _write(tmp_path / "Y" / "Z", "2\n")
    assert _read_layer(tmp_path) == {"X": "1", "Y_Z": "2"}


def test_read_layer_missing_dir(tmp_path):
    assert _read_layer(tmp_path / "nope") == {}


# --- load_env ---


def test_load_env(tmp_path, monkeypatch):
    _write(tmp_path / "API" / "KEY", "secret\n")
    _write(tmp_path / "DEBUG", "1\n")

    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    result = load_env(str(tmp_path))
    assert result == {"API_KEY": "secret", "DEBUG": "1"}
    assert os.environ["API_KEY"] == "secret"
    assert os.environ["DEBUG"] == "1"


def test_load_env_missing_dir():
    result = load_env("/nonexistent_dir_abc123")
    assert result == {}


def test_load_env_strips_trailing_newline(tmp_path):
    _write(tmp_path / "VAL", "hello\n")
    result = load_env(str(tmp_path))
    assert result["VAL"] == "hello"


def test_load_env_system_and_local(tmp_path, monkeypatch):
    system = tmp_path / "system"
    local = tmp_path / "local"
    _write(system / "A", "sys_a\n")
    _write(system / "B", "sys_b\n")
    _write(local / "B", "local_b\n")
    _write(local / "C", "local_c\n")

    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)

    result = load_env(str(local), system_dir=str(system))
    assert result == {"A": "sys_a", "B": "local_b", "C": "local_c"}
    assert os.environ["A"] == "sys_a"
    assert os.environ["B"] == "local_b"
    assert os.environ["C"] == "local_c"


def test_load_env_no_system(tmp_path, monkeypatch):
    _write(tmp_path / "X", "1\n")
    monkeypatch.delenv("X", raising=False)

    result = load_env(str(tmp_path), system_dir=None)
    assert result == {"X": "1"}


def test_load_env_system_dir_missing(tmp_path, monkeypatch):
    local = tmp_path / "local"
    _write(local / "X", "1\n")
    monkeypatch.delenv("X", raising=False)

    result = load_env(str(local), system_dir=str(tmp_path / "nonexistent"))
    assert result == {"X": "1"}


# --- get_env ---


def test_get_env_exists(tmp_path):
    _write(tmp_path / "TOKEN", "abc\n")
    assert get_env("TOKEN", local_dir=str(tmp_path)) == "abc"


def test_get_env_default(tmp_path):
    assert get_env("MISSING", default="fallback", local_dir=str(tmp_path)) == "fallback"


def test_get_env_default_none(tmp_path):
    assert get_env("MISSING", local_dir=str(tmp_path)) is None


def test_get_env_from_system(tmp_path):
    system = tmp_path / "system"
    local = tmp_path / "local"
    local.mkdir()
    _write(system / "TOKEN", "sys_val\n")

    assert get_env("TOKEN", local_dir=str(local), system_dir=str(system)) == "sys_val"


def test_get_env_local_overrides_system(tmp_path):
    system = tmp_path / "system"
    local = tmp_path / "local"
    _write(system / "TOKEN", "sys_val\n")
    _write(local / "TOKEN", "local_val\n")

    assert get_env("TOKEN", local_dir=str(local), system_dir=str(system)) == "local_val"


def test_get_env_system_missing(tmp_path):
    local = tmp_path / "local"
    _write(local / "X", "1\n")
    assert get_env("X", local_dir=str(local), system_dir=str(tmp_path / "nope")) == "1"


# --- set_env ---


def test_set_env_creates_file(tmp_path, monkeypatch):
    monkeypatch.delenv("MY_VAR", raising=False)
    set_env("MY_VAR", "hello", local_dir=str(tmp_path))

    assert (tmp_path / "MY" / "VAR").read_text() == "hello\n"
    assert os.environ["MY_VAR"] == "hello"


def test_set_env_with_slash(tmp_path, monkeypatch):
    monkeypatch.delenv("AI/MODEL", raising=False)
    set_env("AI/MODEL", "gpt", local_dir=str(tmp_path))

    assert (tmp_path / "AI" / "MODEL").read_text() == "gpt\n"


def test_set_env_overwrites(tmp_path, monkeypatch):
    monkeypatch.delenv("X", raising=False)
    set_env("X", "old", local_dir=str(tmp_path))
    set_env("X", "new", local_dir=str(tmp_path))

    assert get_env("X", local_dir=str(tmp_path)) == "new"


def test_set_env_uses_system_path(tmp_path, monkeypatch):
    """set_env reuses the system file's relative path in local."""
    system = tmp_path / "system"
    local = tmp_path / "local"
    _write(system / "AI" / "DEFAULT_MODEL", "old\n")
    local.mkdir()

    monkeypatch.delenv("AI_DEFAULT_MODEL", raising=False)
    set_env("AI_DEFAULT_MODEL", "new", local_dir=str(local), system_dir=str(system))

    # Written to local with same path structure as system
    assert (local / "AI" / "DEFAULT_MODEL").read_text() == "new\n"
    assert os.environ["AI_DEFAULT_MODEL"] == "new"


def test_set_env_does_not_touch_system(tmp_path, monkeypatch):
    system = tmp_path / "system"
    local = tmp_path / "local"
    _write(system / "TOKEN", "sys\n")
    local.mkdir()

    monkeypatch.delenv("TOKEN", raising=False)
    set_env("TOKEN", "local_val", local_dir=str(local), system_dir=str(system))

    # System file unchanged
    assert (system / "TOKEN").read_text() == "sys\n"
    assert (local / "TOKEN").read_text() == "local_val\n"


# --- delete_env ---


def test_delete_env_existing(tmp_path, monkeypatch):
    _write(tmp_path / "A" / "B", "val\n")
    monkeypatch.setitem(os.environ, "A_B", "val")

    assert delete_env("A_B", local_dir=str(tmp_path)) is True
    assert not (tmp_path / "A" / "B").exists()
    assert "A_B" not in os.environ
    assert not (tmp_path / "A").exists()


def test_delete_env_missing(tmp_path):
    assert delete_env("NOPE", local_dir=str(tmp_path)) is False


def test_delete_env_preserves_sibling_dirs(tmp_path, monkeypatch):
    _write(tmp_path / "A" / "B", "1\n")
    _write(tmp_path / "A" / "C", "2\n")
    monkeypatch.setitem(os.environ, "A_B", "1")

    delete_env("A_B", local_dir=str(tmp_path))
    assert (tmp_path / "A").exists()
    assert (tmp_path / "A" / "C").exists()


def test_delete_env_reveals_system(tmp_path, monkeypatch):
    """After deleting local override, system value becomes visible."""
    system = tmp_path / "system"
    local = tmp_path / "local"
    _write(system / "TOKEN", "sys_val\n")
    _write(local / "TOKEN", "local_val\n")

    monkeypatch.setitem(os.environ, "TOKEN", "local_val")
    delete_env("TOKEN", local_dir=str(local))

    assert get_env("TOKEN", local_dir=str(local), system_dir=str(system)) == "sys_val"


# --- list_env ---


def test_list_env(tmp_path):
    _write(tmp_path / "X", "1\n")
    _write(tmp_path / "Y" / "Z", "2\n")

    result = list_env(str(tmp_path))
    assert result == {"X": "1", "Y_Z": "2"}


def test_list_env_does_not_modify_environ(tmp_path, monkeypatch):
    monkeypatch.delenv("ISOLATED_VAR", raising=False)
    _write(tmp_path / "ISOLATED_VAR", "secret\n")

    list_env(str(tmp_path))
    assert "ISOLATED_VAR" not in os.environ


def test_list_env_empty_dir(tmp_path):
    assert list_env(str(tmp_path)) == {}


def test_list_env_merged(tmp_path):
    system = tmp_path / "system"
    local = tmp_path / "local"
    _write(system / "A", "sys_a\n")
    _write(system / "B", "sys_b\n")
    _write(local / "B", "local_b\n")
    _write(local / "C", "local_c\n")

    result = list_env(str(local), system_dir=str(system))
    assert result == {"A": "sys_a", "B": "local_b", "C": "local_c"}


# --- dump_shell ---


def test_dump_shell_bash(tmp_path):
    _write(tmp_path / "KEY", "value\n")
    output = dump_shell(str(tmp_path), shell="bash")
    assert output == "export KEY=value"


def test_dump_shell_bash_with_spaces(tmp_path):
    _write(tmp_path / "KEY", "hello world\n")
    output = dump_shell(str(tmp_path), shell="bash")
    assert output == "export KEY='hello world'"


def test_dump_shell_fish(tmp_path):
    _write(tmp_path / "KEY", "value\n")
    output = dump_shell(str(tmp_path), shell="fish")
    assert output == "set -gx KEY 'value'"


def test_dump_shell_multiple_sorted(tmp_path):
    _write(tmp_path / "B", "2\n")
    _write(tmp_path / "A", "1\n")
    output = dump_shell(str(tmp_path), shell="bash")
    assert output == "export A=1\nexport B=2"


def test_dump_shell_merged(tmp_path):
    system = tmp_path / "system"
    local = tmp_path / "local"
    _write(system / "A", "1\n")
    _write(local / "B", "2\n")

    output = dump_shell(str(local), system_dir=str(system), shell="bash")
    assert output == "export A=1\nexport B=2"


# --- _quote_fish ---


def test_quote_fish_simple():
    assert _quote_fish("hello") == "'hello'"


def test_quote_fish_with_single_quote():
    assert _quote_fish("it's") == "'it\\'s'"


def test_quote_fish_with_backslash():
    assert _quote_fish("a\\b") == "'a\\\\b'"


# --- _detect_shell ---


def test_detect_shell_fish(monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    assert _detect_shell() == "fish"


def test_detect_shell_bash(monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/bash")
    assert _detect_shell() == "bash"


def test_detect_shell_unset(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    assert _detect_shell() == "bash"
