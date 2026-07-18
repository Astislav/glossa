# LayoutSwitcher

Windows tray utility that replaces the system keyboard-layout hotkeys with
its own: a configurable loop hotkey (default `Alt+Shift`) plus optional
per-layout direct hotkeys. Built on [nexus-kit](https://pypi.org/project/nexus-kit/).

## Setup

```bat
uv sync
```

## Run

```bat
uv run python main.py
```

Layout/hotkey configuration lives in `settings/settings.json` (created with
defaults on first run, next to `main.py`). App-level config (paths) — in `.env`.

## Build a shippable exe

```bat
uv run nexus-kit freeze   # once: generate app.spec
uv run nexus-kit build    # every release: dist/LayoutSwitcher.exe + resources/ + .env.example
```
