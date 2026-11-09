# popn_savedata_resetter

**English** | [日本語](README.ja.md)

A tool for modifying pop'n music (PS2) save data stored in PCSX2 memory card images (`.ps2` / `.bin`).
It comes with a GUI (tkinter) and a CLI, both available in Japanese and English.

## Supported titles

pop'n music 7 / 8 / 9 / 10 / 11 / 12 Iroha / BEST HITS!

## Features

| Command | Description |
|---|---|
| `info` | Show the save data found on the card |
| `reset-records` | Reset rankings and records (optionally keeping play counts / clear marks) |
| `set-plays` | Raise the play count of every song and chart to at least N (so songs can be picked in Free Mode) |
| `restore-played` | Write only the "played" info from a backup back into a card that has already been reset |

## Usage

Prebuilt executables are available from [Releases](https://github.com/setsuna-gamer/popn_savedata_resetter/releases) (Windows / macOS / Linux).
You can also run it directly with Python 3:

```bash
python popn_gui.py                                   # GUI
python popn_tool.py info card.ps2
python popn_tool.py --lang en info card.ps2          # choose the display language (ja / en)
python popn_tool.py reset-records card.ps2 --game popn12 --dry-run
python popn_tool.py reset-records card.ps2 --game all --keep plays,extra
python popn_tool.py set-plays card.ps2 --game old --min 1
python popn_tool.py restore-played card.ps2 --from backup.ps2 --game popn7
```

- `--game`: `popn7` `besthits` `popn8` `popn9` `popn10` `popn11` `popn12` `all` (`set-plays` also accepts `old` = popn7/besthits/8/9)
- `--keep`: `plays,extra` / `plays` / `extra` / `none` (what to keep; defaults to each version's default)
- `--dry-run`: preview only, do not write
- `--lang`: display language, `ja` or `en` (place it before the subcommand; defaults to the OS locale or the `POPN_LANG` environment variable)

In the GUI, switch between 日本語 and English with the "Language" box at the top (your choice is remembered).

## Safety

- Before writing, the card is automatically backed up to `backup/` with a timestamp.
- Writing is refused while PCSX2 is running (to avoid corrupting the card). Always quit it first.
- Files are only overwritten at the same size; the FAT and directory structure are never changed. The ECC of written pages is recalculated.
- Keep your own backups of important data in addition to this tool's automatic backup.

## Build

```bash
pip install pyinstaller
python build.py
```

`popn_savedata_resetter_gui` and `popn_savedata_resetter_cli` are produced in `dist/`.
Cross-compilation is not possible, so run it on each OS. Pushing a `v*` tag makes GitHub Actions build for all three OSes and publish to Releases.

## Disclaimer

- **Use at your own risk.** The author is not liable for any damage (such as corrupted or lost save data) caused by using this tool.
- This is an **unofficial** tool and is not affiliated with Konami Amusement / the Konami Group or Sony Interactive Entertainment in any way. **Please do not contact those companies about this tool.**
- "pop'n music", "PlayStation 2" and other names are trademarks or registered trademarks of their respective owners.
- This repository contains no game data (ROMs, disc images, or save data). Use it only with data you legitimately own.
- The project may be **taken down without notice** (repository deleted or made private, Releases withdrawn, etc.).
- Bug reports are accepted via GitHub Issues, but a response is not guaranteed.

## License

[MIT License](LICENSE)
