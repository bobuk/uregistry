# uregistry: Directory-based configuration registry

Your config lives in plain files. File paths become env var names, file content becomes the value. No YAML, no JSON, no `.env` parsers — just a directory tree. 🌳

```
env/
  AI/
    DEFAULT_MODEL    → AI_DEFAULT_MODEL = "claude-sonnet-4-20250514"
    API_KEY          → AI_API_KEY = "sk-..."
  DEBUG              → DEBUG = "1"
```

## Features

- 📁 **Files are config:** Each file is one variable. The path is the name, the content is the value.
- 🔀 **Smart path resolution:** Underscores become directories, or use `/` for explicit control.
- 🐚 **Shell integration:** Generate `export` statements for bash/zsh/fish — drop it into your rc file.
- 🧹 **Zero dependencies:** Pure Python, nothing to install beyond the package itself.
- 🔄 **Read, write, delete:** Full CRUD for your config with automatic directory cleanup.

## Installation

```bash
pip install uregistry
```

## Quick Start

```python
from uregistry import load_env, get_env, set_env, delete_env, list_env, dump_shell

# Load all vars from env/ into os.environ
load_env()
load_env("path/to/env")

# Read a single var (does not modify os.environ)
model = get_env("AI_DEFAULT_MODEL")
model = get_env("AI_DEFAULT_MODEL", default="gpt-4o")

# Write a var (creates dirs as needed, updates os.environ)
set_env("AI/API_KEY", "sk-new-key")
set_env("DEBUG", "1")

# Delete a var (removes file, cleans empty dirs)
delete_env("DEBUG")

# List all vars without modifying os.environ
all_vars = list_env()

# Generate shell export statements
print(dump_shell())                    # bash/zsh format
print(dump_shell(shell="fish"))        # fish format
```

## Path Resolution

Use `/` in names to set explicit directory boundaries:

```python
set_env("AI/CRON_MODEL", "haiku")   # → env/AI/CRON_MODEL
```

Without `/`, underscores become directory separators automatically:

```python
set_env("AI_MODEL", "sonnet")       # → env/AI/MODEL
```

If a file already exists that matches the full var name, it wins — no ambiguity.

## Shell Integration

Drop this into your `.bashrc` / `.zshrc` and your env dir becomes the source of truth for your shell:

```sh
eval "$(python -m uregistry.registry)"
```

Or for fish, in `config.fish`:

```fish
python -m uregistry.registry --shell fish | source
```

Auto-detects your shell when run directly, so `python -m uregistry.registry` just works. 🐟

## Why?

- **`dotenv` files** get messy — merge conflicts, quoting bugs, one giant blob.
- **Directory trees** are git-friendly, diffable, and you can manage individual vars with standard Unix tools (`cat`, `echo >`, `rm`).
- **Secret management** fits naturally — just gitignore sensitive subtrees.

## Contributing

Pull requests and issues are welcome!

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create a new Pull Request

## License

MIT
