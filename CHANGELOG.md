# Changelog

## 0.2.0 — 2026-10-13

- **Command and option names are now English only**: `list`, `choose`, `auto`, `menu install|remove`,
  `--title`, `--count`, `--text` (were `liste`, `choisir`, `menu installer|retirer`, `--titre`,
  `--nombre`, `--texte`). The interface still follows the system language (English, or French).
- **`list --json` keys are now English**: `path`, `guessit_name`, `recognized` (`type`: `movie` or
  `episode`, `title`), `embedded`, `external`, `candidate_count`, `min_score`, `kept_count`,
  `candidates` (`provider`, `id`, `score`, `max_score`, `percent`, `hash_match`, `release`, `language`,
  `hearing_impaired`, `machine_translated`, `fps`).
- **Code in English**: modules, names, comments and tests (`analysis`, `search`, `saving`, `choose`,
  `texts`…); only the displayed texts are translated.
- **Update from 0.1.0**: after reinstalling, run `subdolphin menu install` once; it replaces the old
  menu file (`subdolphin-choisir.desktop`, which ran the old `choisir` command).

## 0.1.0 — 2026-10-13

First public version.

- **Choose a subtitle…** (`subdolphin choisir`, now `choose`): every subtitle at or above `min_score`, best first,
  with score, hash match, provider, release, hearing impaired, machine translated and frame rate; title
  correction; languages and categories for the current search; download, save without overwriting,
  duplicate detection.
- **Best subtitle automatically** (`subdolphin auto`): files and folders, as `subliminal download` with
  the same configuration; progress bar with Cancel; summary.
- **Dolphin menu** (`subdolphin menu installer|retirer`, now `install|remove`): "Subtitles" submenu.
- **Search only** (`subdolphin liste`, now `list`), as text or JSON.
- Reads subliminal's configuration (`subliminal.toml`) and shares its cache.
- French and English interface.
