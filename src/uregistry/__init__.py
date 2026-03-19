"""
uregistry — Directory-based configuration registry.

File paths become env var names, file content becomes the value.
"""

from uregistry.registry import (
    delete_env,
    dump_shell,
    get_env,
    list_env,
    load_env,
    set_env,
)

__all__ = [
    "delete_env",
    "dump_shell",
    "get_env",
    "list_env",
    "load_env",
    "set_env",
]
