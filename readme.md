<img src="resources/logo.svg" width="88" align="right" alt="Glossa logo">

# Glossa

**Your layout-switch hotkey cycles only the languages you choose. The rest
get their own hotkeys.**

You touch-type in two languages and flip between them with your usual
hotkey — `Alt+Shift`, `Ctrl+Shift`, whatever your fingers learned years ago.
Then you start learning a third language, add its keyboard layout, and
Windows quietly ruins everything: the same hotkey now cycles through *three*
layouts, and every switch becomes a guessing game. Windows has no native way
to say *"cycle these two, and give that one its own hotkey"*.

Glossa is a small Windows tray app that does exactly that. (Named after
γλώσσα — *language* in Greek, the language it was built to learn.)

## What it does

- **Carousel** — your switch hotkey cycles only the layouts you check.
  Your two-language rhythm stays intact. On first run Glossa reads the
  hotkey you already use from Windows settings and adopts it — `Alt+Shift`
  people and `Ctrl+Shift` people both keep their habit.
- **Direct hotkeys** — give any layout its own combo, e.g. `Alt+Shift+G`
  for Greek. Press it only when you actually want that language.
- **Smart conflict handling** — `Alt+Shift` and `Alt+Shift+G` coexist
  correctly: the longer combo fires instantly on key press; the shorter one
  fires on release, only if the longer one didn't intervene. No double
  switches, no false triggers.
- **It remembers where you were** — typing Russian → jump to Greek → press
  the carousel hotkey → you're back in Russian, not in a random slot.
- **Responsive by design** — hotkey detection runs in a lightweight hook;
  the actual switching happens off the input path, so your keystrokes are
  never delayed.
- Autostart with Windows (a checkbox), single-instance guard, and the
  system's own layout hotkeys are disabled while the app runs — and restored
  when it exits, even after a crash.

## Who it's for

Anyone who types in more languages than they cycle: language learners,
translators, expats, developers writing code in English and chatting in
their native language while studying a third one.

## Install

1. Download `Glossa.exe` from
   [Releases](https://github.com/Astislav/Glossa/releases) and run it.
2. Find the tray icon → double-click → check the layouts for the carousel,
   assign direct hotkeys, save. Done.

> **Windows SmartScreen note.** The binary is not code-signed (signing
> certificates are paid), so on first run SmartScreen may show "Windows
> protected your PC". Click **More info → Run anyway**. The app is open
> source and every release is built from this repository by a public GitHub
> Actions workflow — or build it yourself in two commands (below).

Settings live next to the exe in `settings/settings.json`; optional
app-level config in `.env` (see `.env.example`).

## Коротко по-русски

Glossa — трей-утилита для Windows для тех, кто печатает на двух языках и
учит третий. Ваш привычный хоткей (`Alt+Shift` или `Ctrl+Shift` —
подхватывается из настроек системы автоматически) переключает только
выбранные раскладки, а третьему языку назначается свой хоткей, например
`Alt+Shift+G` для греческого. Никакой карусели из трёх языков, ломающей
слепую печать: комбинации не конфликтуют, приложение помнит, на каком языке
вы писали до переключения. Автозапуск — галочкой в настройках.

## Run from source

```bat
uv sync
uv run python main.py
```

## Build your own exe

```bat
uv sync
uv run nexus-kit build    # → dist/Glossa.exe
```

## Tests

```bat
uv run pytest
```

The hotkey engine (prefix-conflict resolution, carousel memory, settings
round-trip) is covered by unit tests; releases run them in CI before
building.

## License

[MIT](LICENSE)
