# CLAUDE.md

Guidance for AI coding agents working on this repository.
`CLAUDE.md` and `AGENTS.md` are **identical on purpose** — see "Keeping CLAUDE.md and AGENTS.md in sync" below.

## Project overview

`popn_savedata_resetter` modifies pop'n music (PS2) save data stored in PCSX2 memory card images (`.ps2` / `.bin`).
It ships a tkinter GUI and an argparse CLI, both bilingual (Japanese / English). Pure Python 3, standard library only
(PyInstaller is needed only for building executables).

Supported titles: pop'n music 7, BEST HITS!, 8, 9, 10, 11, 12 Iroha.

## Repository layout

| File | Role |
|---|---|
| `popn_tool.py` | CLI and all save-editing logic: per-title `PROFILES`, checksum, `reset_records`, `set_min_plays`, `restore_played`, `cmd_*` handlers, `main()` |
| `popn_gui.py` | tkinter GUI. Thin wrapper that builds `argparse.Namespace` objects and calls the `cmd_*` functions with stdout captured |
| `ps2mc.py` | PS2 memory card image reader/writer (FAT, directories, same-size file overwrite, ECC recalculation) |
| `i18n.py` | All user-visible strings (`MESSAGES`), language detection, `t(key, **kw)` |
| `snap.py` | Dev helper: dump save files from a card (`take`) and byte-diff two snapshots (`diff`) for reverse engineering |
| `build.py` | PyInstaller build (GUI + CLI executables into `dist/`) |
| `.github/workflows/build.yml` | CI: builds on 3 OSes on `v*` tags, zips the binaries with docs/license, publishes a GitHub Release |
| `README.md` / `README.ja.md` | User docs (English / Japanese) |

## Commands

```bash
python popn_gui.py                                          # run the GUI
python popn_tool.py info card.ps2
python popn_tool.py reset-records card.ps2 --game popn12 --dry-run
python popn_tool.py reset-records card.ps2 --keep plays,extra    # --game omitted => all titles, asks to confirm (--yes/-y skips)
python popn_tool.py set-plays card.ps2 --game old --min 1
python popn_tool.py restore-played card.ps2 --from backup.ps2 --game popn7
python popn_tool.py --lang en info card.ps2                 # --lang goes BEFORE the subcommand
pip install pyinstaller && python build.py                  # build executables for the current OS
```

There is no test suite. Verify changes by importing the modules, running the CLI with `--dry-run`
against a card image you own, and (for GUI changes) instantiating `App` and calling `change_lang()`.
Never commit card images, backups or game data (`*.ps2`, `*.bin`, `backup/`, `snapshots/`, `dump/` are git-ignored).

## Architecture and key concepts

- **Save location**: each title keeps one save file inside a card directory named by its product code
  (`PROFILES[...]["dir"]`, e.g. `BISLPM-66314popn12`). `ALL_DIRS` also lists popn13/14, which are detected by `info` but unsupported.
- **Checksum**: a single byte = sum of all preceding bytes mod 256, located within the last 16 bytes
  (`find_checksum_pos`). It must be recomputed (`fix_checksum`) after every edit; if it cannot be located uniquely, abort.
- **Ranking table**: 12-byte entries (u32 score + 8-byte name), 5 per group, `groups` groups. Reset to `DEFAULT_RANK` / `"POPN"`.
- **Records region** (`records` in a profile) has two modes:
  - `zero`: fill the whole region with zeros (popn12).
  - `slots`: 12-byte slots `<IHHI` = score, play count, combo, extra (clear marks). Only slots that look valid
    (`score <= 100000`, `plays < 2000`, `combo < 2000`, `extra < 16`) are touched. For titles whose default score is 10000,
    slots with score 0 are padding outside song data and must be left alone.
  - `keep` selects which fields survive a reset: `plays`, `extra`. Titles 7/8/9/BEST HITS default to keeping both
    because song unlock state depends on "played" info; 10/11 default to none.
- **Writes**: `ps2mc.Card.write_file` only overwrites a file with data of the *same size*; FAT/directory structures are never changed.
  ECC of every written page is recomputed. Supports both 528-byte (with spare) and 512-byte page images.
- **Safety rails** (keep them when changing write paths): refuse to write while PCSX2 is running (`pcsx2_running`);
  timestamped backup into `backup/` next to the executable/script (`backup`, `HERE`) before any write; `--dry-run` writes nothing;
  all jobs are computed first and written only after every title passes validation.
- **Frozen builds**: `HERE` resolves next to the PyInstaller executable (and outside the `.app` bundle on macOS) so `backup/` and the GUI settings file live beside it.
- **Title order** in `PROFILES`, `ALL_DIRS`, `OLD_GAMES`, docs and GUI is: `popn7`, `besthits`, `popn8`, `popn9`, `popn10`, `popn11`, `popn12`. Keep it consistent everywhere.

## Adding or changing a title

1. Reverse engineer with `snap.py take` / `diff` on cards before/after in-game actions to find ranking/records offsets.
2. Add a `PROFILES` entry (title, `dir`, `ranking`, `records`, optional `keep`), add it to `ALL_DIRS` if missing and to `OLD_GAMES` if appropriate.
3. Verify with `--dry-run` that the changed-byte count is plausible, and test in the emulator before releasing.
4. Update the supported-title lists in both READMEs and this file.

## Internationalization rules

- Every user-visible string (CLI output, errors passed to `sys.exit`, GUI labels, dialogs, `ps2mc` errors) goes through `i18n.t("key")`.
  Add the key to `MESSAGES` with both `ja` and `en`. Do not hard-code display text elsewhere.
- Language resolution order: `--lang` (CLI) / saved choice (GUI) → `POPN_LANG` env var → OS locale → English fallback.
- The GUI language selector rebuilds the whole widget tree (`App.build`). Keep widget state in `tk` variables created in `__init__`,
  and store language-independent values (e.g. `KEEP_KEYS`) rather than translated labels.
- The GUI saves its language choice to `popn_savedata_resetter.json` next to the script/executable (git-ignored).
- English display replaces "いろは" with "Iroha" via `title_of()`. Argument names and `--game` values are never translated.
- Docstrings and code comments in `popn_tool.py` / `ps2mc.py` / `snap.py` are largely Japanese; new comments may be written in either language.

## Defaults and CLI behavior (decided with the maintainer)

- GUI "Reset records" target defaults to `all`.
- CLI `reset-records` without `--game` targets all titles and asks `[y/N]` first (EOF counts as "no"); `--dry-run` and `--yes/-y` skip the prompt.
  The GUI always passes an explicit game, so it never prompts.
- `set-plays` defaults to `--game old` (popn7 / besthits / popn8 / popn9).

## Release process

- CI (`build.yml`) runs on `v*` tags and on manual dispatch. The release job zips each OS's `dist/*` together with
  `README.md`, `README.ja.md` and `LICENSE`, then publishes via `softprops/action-gh-release`.
- To re-release `v1.0`: merge to `main`, delete the existing release and tag (`gh release delete v1.0 --cleanup-tag`),
  re-create the tag on `origin/main` and push it. Wait for any in-progress run to finish first.
- PyInstaller cannot cross-compile; executables must be built on each target OS (CI handles this).

## Git workflow

- Work on a feature branch, open a PR against `main`, merge with a merge commit.
- Commit messages are short imperative sentences (e.g. "Add README", "Reorder target titles: popn7, besthits, popn8-12").
- If `main` moves, merge `origin/main` into the branch and resolve conflicts; README changes usually need to be applied to both languages.
- Do not rewrite published history. Re-pointing the `v1.0` tag is the one accepted exception and only when the maintainer asks.

## Legal and content policy

- MIT licensed. The README disclaimer (use at own risk, unofficial, no affiliation with Konami or Sony, possible takedown) must stay in both READMEs.
- Never add game data (ROMs, disc images, save data) to the repository.
- Do not put personal information in committed files: no local file paths, usernames, e-mail addresses, API keys or tokens.

## Keeping CLAUDE.md and AGENTS.md in sync

`CLAUDE.md` and `AGENTS.md` must be byte-for-byte identical. Edit one, then copy it over the other
(`cp CLAUDE.md AGENTS.md`). The `check-docs` GitHub Actions workflow fails if they differ.
