# subdolphin

*[Version française](README.fr.md)*

Subtitles from Dolphin's right-click menu, powered by [subliminal](https://github.com/Diaoul/subliminal).

subdolphin adds a **Subtitles** submenu to Dolphin (KDE Plasma 6):

- **Choose a subtitle…** (one video): lists every subtitle subliminal finds, best first, and lets you
  pick one, even when the video already has subtitles (the ones that are there may not suit you).
- **Best subtitle automatically** (videos and/or folders): does what `subliminal download` does with
  the same configuration, then shows a summary.

subdolphin is a thin layer around subliminal. Search, scoring, download and configuration are
subliminal's own (same `subliminal.toml`). subdolphin adds the windows (kdialog) and a few rules:

- it **never overwrites** a file: `Film.fr.srt`, then `Film.<provider>.fr.srt`, `Film.<provider>-2.fr.srt`…;
- it does not save a subtitle identical to one already next to the video;
- it shows what is already there: subtitle files, embedded tracks (text or image, forced, hearing
  impaired).

## Requirements

- Linux with KDE Plasma 6 and Dolphin (KIO 6), `kdialog`, `qdbus6` (or `qdbus`).
- Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).
- A subliminal configuration file, `~/.config/subliminal/subliminal.toml`, with at least a language (see
  [Configuration](#configuration)). subliminal itself (2.7.x) is installed as a dependency.

## Installation

```bash
uv tool install git+https://github.com/erratos/subdolphin
subdolphin menu install
```

- If you also use the `subliminal` command, install both with **the same Python** (`--python`, e.g.
  `--python /usr/bin/python3.14`): they share a cache whose file format depends on Python (see
  [Troubleshooting](#troubleshooting)).
- `subdolphin menu install` writes two service menus to `~/.local/share/kio/servicemenus/`
  (executable, as KDE requires). They run the `subdolphin` command that installed them, by absolute path:
  run it again if the command moves.
- Restart Dolphin if the menu does not show up.

## Usage

### In Dolphin

**Right-click one video → Subtitles → Choose a subtitle…**

1. A window shows the recognised title (in bold), what is already there, then:
   - **↻ Correct the title and search again…**;
   - **⚙ Options for this search**: languages and categories (regular, hearing impaired, forced), for
     this search only; starting values come from `subliminal.toml`, nothing is saved;
   - every subtitle at or above `min_score`, best first: score, ★ (hash match: sync guaranteed),
     provider, release name, `HI` (hearing impaired), `MT` (machine translated), frame rate.
2. Select a line and press OK (kdialog lists do not handle double-click).
3. The subtitle is downloaded and saved next to the video; a notification gives its name.

If the title is not recognised, you are asked to type it: `Title (year)` for a movie,
`Series S01E02` for an episode.

**Right-click videos and/or folders → Subtitles → Best subtitle automatically**

- Folders are searched with their subfolders; hidden folders, `sample` files and folders, and symbolic
  links found inside folders are ignored, as subliminal does.
- Videos that already have a subtitle in the wanted language (file or embedded track) are skipped,
  unless `force` is set (see below).
- A progress bar (with Cancel), then a summary: saved, already had subtitles, nothing found, title not
  recognised, identical to an existing subtitle, errors.

### Command line

The interface follows the system language: English, or French on a French system.

```bash
subdolphin list VIDEO [--title "Title (year)"] [-n N] [--json]   # search only, nothing downloaded
subdolphin choose VIDEO                                          # "Choose a subtitle…" (windows)
subdolphin auto PATH… [--text]                                   # automatic; --text: in the terminal
subdolphin menu install | remove                                 # install / remove the Dolphin menu
subdolphin --debug …                                             # show subliminal's log
subdolphin --config FILE …                                       # another subliminal.toml
```

`subdolphin COMMAND --help` describes each step in terms of subliminal, with the closest `subliminal`
command.

## Configuration

subdolphin has no configuration of its own: it reads subliminal's file
(`~/.config/subliminal/subliminal.toml`), with the same rules as the `subliminal` command.

| Setting (`[download]` unless noted) | Effect in subdolphin |
|---|---|
| `language` | languages searched (required) |
| `provider`, `extend_provider`, `ignore_provider` | providers used |
| `refiner`, `extend_refiner`, `ignore_refiner` | refiners used |
| `name` | sed-like substitutions of the name passed to guessit (see pitfalls) |
| `min_score` | threshold, in % of the maximum score, for the list and the automatic mode |
| `subtitle_categories` | e.g. `"n,fo"`: regular and forced, no hearing impaired; `"fo"`: forced only |
| `skip_wrong_fps` | automatic mode: skip subtitles whose frame rate does not match |
| `force`, `force_external_subtitles`, `force_embedded_subtitles` | automatic mode: download even if the language is already there |
| `encoding`, `subtitle_format`, `language_format` | how subtitles are written (UTF-8 by default) |
| `max_workers` | providers queried in parallel |
| `[provider.*]`, `[refiner.*]` | credentials and options |
| `[default] cache_dir` | cache, shared with the `subliminal` command |

Example with recommended settings (see pitfalls below):

```toml
[download]
language = ["fr"]
min_score = 50
subtitle_categories = "n,fo"
name = ['s|^/run/media/[^/]+/[^/]+/||']
ignore_refiner = ["omdb"]
ignore_provider = ["podnapisi"]

[provider.opensubtitlescom]
username = "your-username"   # the username, not the e-mail address
password = "…"
max_result_pages = 10

[provider.addic7ed]
username = "…"
password = "…"

[refiner.tmdb]
apikey = "…"                 # TMDB API key (v3)
```

The file holds passwords and keys: keep it private (`chmod 600`).

### Pitfalls (subliminal 2.7.1)

- **guessit reads the whole path.** A mount point such as `/run/media/user/Disk Name/…` can be taken for
  the title, and turn a movie into an "episode". subdolphin removes `/run/media/<user>/<disk>/` and
  `/media/<user>/<disk>/` by default, after your own `name` patterns.
- **OMDb** keeps the first result of the right year, which can be another movie with the same title; the
  wrong IMDb id then favours the wrong subtitles. Use TMDB instead: `ignore_refiner = ["omdb"]`.
- **OpenSubtitles.com paginates without limit**: a title-only search can reach page 21, get an HTTP 400
  error and lose every result. Set `max_result_pages = 10`.
- **OpenSubtitles.com** logs in with the *username*, not the e-mail address, and only when downloading.
- **OpenSubtitles.com uses the video hash only if the `opensubtitles` provider is enabled too** (fixed in
  subliminal after 2.7.1, [#1382](https://github.com/Diaoul/subliminal/issues/1382)): do not ignore it.
- **addic7ed, gestdown and tvsubtitles only handle episodes**, never movies.
- **podnapisi** was unreachable when this was written (October 2026).

## Saved file names

| Situation | Name |
|---|---|
| no subtitle in this language yet | `Film.fr.srt` (`Film.fr.hi.srt` if hearing impaired) |
| one is already there | `Film.<provider>.fr.srt`, e.g. `Film.opensubtitlescom.fr.srt` |
| that name is taken | `Film.<provider>-2.fr.srt`, `-3`… |

mpv recognises the language only when it is the last part of the name (optionally followed by `hi`,
`sdh` or `forced`); subliminal's own `[hi]` suffix is not understood by mpv, hence `.fr.hi`. The name is
reserved before writing (exclusive creation), so nothing is ever overwritten, even by two runs at once.

subliminal itself only recognises names like `Film.fr.srt`: for it, `Film.<provider>.fr.srt` has an
undetermined language. The automatic mode may therefore later add a `Film.fr.srt`, without overwriting
anything.

## Troubleshooting

- **See what happens**: run `subdolphin --debug choose VIDEO` (or `list`, or `auto --text`) in a
  terminal. Like `subliminal --debug`, the log may show an OpenSubtitles.org session token: do not paste
  it publicly.
- **Closest `subliminal` command** (downloads into a separate folder, leaves the video's files alone):
  `subliminal --debug download -l fr --force -d /tmp/test VIDEO`.
- **"Download from opensubtitlescom failed" although the quota is fine**: check that `subliminal` and
  `subdolphin` run on the same Python. The shared cache (`~/.cache/subliminal/subliminal.dbm*`) is a dbm
  file whose format depends on Python: Python 3.13+ creates SQLite-based files that Python 3.12 cannot
  read, and the reverse also happens. subliminal silently ignores cache errors, which breaks the
  OpenSubtitles.com login (its token is kept in the cache) and the TMDB lookups. Fix: reinstall both
  tools with the same `--python`, then delete the old cache file; it rebuilds itself.
- **No menu**: run `subdolphin menu install` again and restart Dolphin. The menu appears only on local
  files: "Choose…" for exactly one video, "Best subtitle automatically" for videos and folders; it is
  hidden when the selection contains other files.

## Update and uninstall

```bash
uv tool install --reinstall git+https://github.com/erratos/subdolphin   # add the same --python as before
subdolphin menu install                                                 # after an update: refresh the menu
subdolphin menu remove                                                  # uninstall: remove the menu…
uv tool uninstall subdolphin                                            # …then the command
```

## Development

```bash
git clone https://github.com/erratos/subdolphin
cd subdolphin
uv sync
uv run pytest
uv run subdolphin list VIDEO
```

Tests never use the network (it is blocked in `tests/conftest.py`). Code, names and comments are in
English; only the displayed texts are translated (`texts.py`). Layout of `src/subdolphin/`:

| Module | Role |
|---|---|
| `config.py` | reads `subliminal.toml` with the rules of subliminal's command line |
| `analysis.py` | recognises the video (`scan_video`), embedded tracks, existing subtitles |
| `search.py` | refiners, candidate list, scores, threshold, download |
| `saving.py` | file names, duplicates, writing without overwriting |
| `choose.py` | "Choose a subtitle…" flow, independent of the windows |
| `auto.py` | automatic mode |
| `ui_kdialog.py`, `ui_terminal.py` | kdialog windows, terminal output |
| `menu.py` | Dolphin service menus |
| `texts.py` | interface texts (French, English) |
| `cli.py` | command line |

## License

[MIT](LICENSE), like subliminal.
