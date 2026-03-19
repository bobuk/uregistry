# uregistry

Directory-based configuration registry. File paths become env var names, file content becomes the value.

```
env/
  AI/
    DEFAULT_MODEL    → AI_DEFAULT_MODEL = "claude-sonnet-4-20250514"
    API_KEY          → AI_API_KEY = "sk-..."
  DEBUG              → DEBUG = "1"
```

## Install

```sh
pip install uregistry
```

## Usage

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

Use `/` in names to set explicit directory boundaries:

```python
set_env("AI/CRON_MODEL", "haiku")   # → env/AI/CRON_MODEL
```

Without `/`, underscores become directory separators:

```python
set_env("AI_MODEL", "sonnet")       # → env/AI/MODEL
```

## Shell integration

Add to your `.bashrc` / `.zshrc`:

```sh
eval "$(python -m uregistry.registry)"
```

Or for fish, in `config.fish`:

```fish
python -m uregistry.registry --shell fish | source
```

## License

MIT
