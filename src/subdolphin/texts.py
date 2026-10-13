"""Interface texts (French, English), chosen from the system language."""

from __future__ import annotations

import os

TEXTS: dict[str, dict[str, str]] = {
    'fr': {
        'cli.description': 'Sous-titres depuis le clic droit de Dolphin, avec subliminal.',
        'cli.config': 'fichier de configuration de subliminal (par défaut : {path})',
        'cli.debug': 'affiche le journal de subliminal (comme `subliminal --debug`)',
        'cli.list': 'affiche les meilleurs sous-titres trouvés pour une vidéo, sans rien télécharger',
        'cli.list_epilog': (
            'Toutes les étapes sont faites par subliminal, avec sa configuration :\n'
            '  scan_video (nom passé à guessit : [download] name), refiners (metadata, hash, tmdb…),\n'
            '  AsyncProviderPool.list_subtitles, puis tri de download_best_subtitles\n'
            '  (subtitle_categories, puis compute_score).\n\n'
            'Pour voir ce qui se passe :\n'
            '  subdolphin --debug list VIDÉO\n\n'
            'Commande subliminal la plus proche (télécharge le meilleur dans un dossier à part,\n'
            'sans toucher aux fichiers de la vidéo) :\n'
            '  subliminal --debug download -l fr --force -d /tmp/essai VIDÉO'
        ),
        'cli.choose': 'parcours interactif (fenêtres kdialog) : choisir un sous-titre et l\'enregistrer',
        'cli.choose_epilog': (
            'Mêmes étapes que « list » (toutes faites par subliminal, avec sa configuration), puis :\n'
            '  download_subtitles (source choisie) et save_subtitles (nom réservé d\'abord :\n'
            '  aucun fichier existant n\'est jamais écrasé).\n\n'
            'Pour voir ce qui se passe, dans un terminal :\n'
            '  subdolphin --debug choose VIDÉO'
        ),
        'cli.auto': 'meilleur sous-titre pour chaque vidéo (fichiers ou dossiers), sans question, puis bilan',
        'cli.auto_epilog': (
            'Fait ce que fait « subliminal download » avec la même configuration :\n'
            '  vidéos déjà pourvues sautées (sauf force, force_external_subtitles,\n'
            '  force_embedded_subtitles) ; choix par download_best_subtitles (min_score,\n'
            '  subtitle_categories, skip_wrong_fps), qui passe au suivant si un téléchargement\n'
            '  échoue ; enregistrement sans écraser (nom réservé, puis save_subtitles).\n'
            'Dans un dossier, les liens symboliques sont ignorés (collect_video_filepaths).\n\n'
            'Pour voir ce qui se passe, dans un terminal :\n'
            '  subdolphin --debug auto --text CHEMIN…\n\n'
            'Commande subliminal la plus proche (télécharge dans un dossier à part) :\n'
            '  subliminal --debug download -l fr -d /tmp/essai CHEMIN…'
        ),
        'cli.menu': 'installe ou retire le sous-menu « Sous-titres » du clic droit de Dolphin',
        'cli.menu_action': 'install : installer (ou mettre à jour) ; remove : retirer',
        'cli.menu_epilog': (
            'Deux fichiers dans ~/.local/share/kio/servicemenus/ (exécutables, comme KDE l\'exige) :\n'
            '  subdolphin-choose.desktop : « Choisir un sous-titre… », une seule vidéo ;\n'
            '  subdolphin-auto.desktop : « Meilleur sous-titre automatique », vidéos et dossiers.\n'
            'Ils lancent la commande subdolphin utilisée pour les installer (chemin absolu).'
        ),
        'cli.video': 'vidéo à analyser',
        'cli.paths': 'vidéos ou dossiers',
        'cli.title': 'titre à utiliser à la place du nom de fichier, ex. « The Fall (2006) »',
        'cli.count': 'nombre de candidats affichés (défaut : {n})',
        'cli.count_all': 'nombre de candidats affichés (défaut : tous)',
        'cli.json': 'sortie JSON',
        'cli.text': 'dans le terminal, sans fenêtre',
        'err.config_toml': 'Configuration illisible ({path}) : {error}',
        'err.config_language': 'Aucune langue dans [download] language de {path}',
        'err.config_name': 'Motif de nom incorrect dans [download] name de {path} : {error}',
        'err.video': 'Vidéo inutilisable : {error}',
        'err.kdialog': 'kdialog est introuvable : il sert à afficher les fenêtres de « choose ».',
        'list.video': 'Vidéo : {name}',
        'list.guessit_name': 'Nom analysé : {name}',
        'list.movie': 'Reconnu : film « {title} »',
        'list.episode': 'Reconnu : épisode « {title} »',
        'list.unrecognized': 'Titre non reconnu : relancer avec --title "Titre (année)"',
        'list.embedded': 'Pistes intégrées :',
        'list.embedded_none': 'Pistes intégrées : aucune',
        'list.external': 'Déjà présents :',
        'list.external_none': 'Déjà présents : aucun',
        'list.none': 'Aucun sous-titre trouvé.',
        'list.header': '  #  Score     ★  Source            HI  TA  fps     Version',
        'list.total': '{n} candidat(s) trouvé(s), {shown} affiché(s).',
        'list.total_threshold': '{n} candidat(s) trouvé(s), dont {kept} à {threshold} % ou plus ; {shown} affiché(s).',
        'list.legend': '★ : empreinte (synchro assurée) ; HI : malentendants ; TA : traduction automatique',
        'mark.machine_translated': 'TA',
        'kind.text': 'texte',
        'kind.image': 'image',
        'kind.unknown': 'nature inconnue',
        'track.forced': 'forcé',
        'track.hearing_impaired': 'malentendants',
        'language.unknown': 'langue inconnue',
        'language.fr': 'français',
        'language.en': 'anglais',
        'ui.title': 'Sous-titres',
        'ui.video_error': 'Vidéo inutilisable : {error}',
        'ui.read_only': 'Impossible d\'écrire dans « {folder} » : aucun sous-titre ne pourrait y être enregistré.',
        'ui.title_not_found': (
            'Titre non reconnu pour « {name} ».\n\n'
            'Titre à rechercher (film : « Titre (année) » ; épisode : « Série S01E02 ») :'
        ),
        'ui.still_not_found': (
            '« {title} » n\'est pas reconnu.\n\n'
            'Titre à rechercher (film : « Titre (année) » ; épisode : « Série S01E02 ») :'
        ),
        'ui.correct_title': 'Titre à rechercher (film : « Titre (année) » ; épisode : « Série S01E02 ») :',
        'ui.searching': 'Recherche des sous-titres pour « {title} »…',
        'ui.none_found': '« {title} » : aucun sous-titre trouvé.',
        'ui.found': '« {title} » : {n} sous-titre(s) trouvé(s)',
        'ui.found_threshold': '« {title} » : {n} sous-titre(s) trouvé(s), dont {kept} à {threshold} % ou plus',
        'ui.order_all': ', du meilleur au moins bon.',
        'ui.order_limited': ' ; voici les {shown} meilleurs.',
        'ui.present': 'Déjà présents : {items}',
        'ui.embedded': 'Pistes intégrées : {items}',
        'ui.legend': '★ synchro assurée · HI malentendants · TA traduction automatique',
        'ui.line_correct': '↻ Corriger le titre et relancer la recherche…',
        'ui.line_options': '⚙ Options de cette recherche : {summary}…',
        'ui.options_summary': 'langues {languages} · {categories}',
        'ui.all_categories': 'toutes catégories',
        'ui.options': (
            'Options de cette recherche seulement (rien n\'est enregistré ;\n'
            'valeurs de départ : subliminal.toml) :'
        ),
        'ui.option_language': 'Langue : {name}',
        'ui.category_n': 'Sous-titres normaux',
        'ui.category_hi': 'Malentendants (HI)',
        'ui.category_fo': 'Forcés (passages en langue étrangère seulement)',
        'ui.category_short_n': 'normaux',
        'ui.category_short_hi': 'HI',
        'ui.category_short_fo': 'forcés',
        'ui.options_incomplete': 'Il faut au moins une langue et une catégorie : options inchangées.',
        'ui.fps': '{fps} i/s',
        'ui.downloading': 'Téléchargement depuis {provider}…',
        'ui.download_failed': (
            'Le téléchargement depuis {provider} a échoué.\n\n'
            'Pour voir pourquoi, dans un terminal :\n'
            'subdolphin --debug choose "{path}"'
        ),
        'ui.duplicate': 'Ce sous-titre est identique à « {name} », déjà présent : il n\'a pas été recréé.',
        'ui.save_error': 'Échec de l\'enregistrement : {error}',
        'ui.saved': 'Enregistré : {name}',
        'auto.start': 'Sous-titres automatiques : {n} vidéo(s)…',
        'auto.video': 'Vidéo {index} / {total} : {name}',
        'auto.read_only': 'dossier en lecture seule',
        'auto.summary_title': 'Sous-titres automatiques : {n} vidéo(s)',
        'auto.no_video': (
            'Aucune vidéo trouvée.\n'
            '(Dans un dossier, les liens symboliques sont ignorés, comme par subliminal.)'
        ),
        'auto.saved': 'Enregistrés : {n}',
        'auto.already_have': 'Déjà pourvues, sautées : {n}',
        'auto.nothing_found': 'Rien trouvé à {threshold} % ou plus : {n}',
        'auto.nothing_found_no_threshold': 'Rien trouvé : {n}',
        'auto.unrecognized': 'Titre non reconnu (utiliser « Choisir un sous-titre… ») : {n}',
        'auto.duplicates': 'Identiques à un sous-titre déjà présent : {n}',
        'auto.errors': 'Erreurs : {n}',
        'auto.error_line': '    {name} : {error}',
        'auto.more': '… et {n} autre(s)',
        'auto.cancelled': 'Annulé après {done} vidéo(s) sur {total}.',
        'auto.help': 'Pour le détail, dans un terminal : subdolphin --debug auto --text CHEMIN…',
        'menu.installed': 'Menu « Sous-titres » installé ; il lance : {command}',
        'menu.removed': 'Menu « Sous-titres » retiré.',
        'menu.none': 'Aucun menu de subdolphin à retirer.',
    },
    'en': {
        'cli.description': "Subtitles from Dolphin's context menu, with subliminal.",
        'cli.config': 'subliminal configuration file (default: {path})',
        'cli.debug': "show subliminal's log (like `subliminal --debug`)",
        'cli.list': 'show the best subtitles found for a video, without downloading anything',
        'cli.list_epilog': (
            'Every step is done by subliminal, with its configuration:\n'
            '  scan_video (name passed to guessit: [download] name), refiners (metadata, hash, tmdb…),\n'
            '  AsyncProviderPool.list_subtitles, then the download_best_subtitles ordering\n'
            '  (subtitle_categories, then compute_score).\n\n'
            'To see what happens:\n'
            '  subdolphin --debug list VIDEO\n\n'
            'Closest subliminal command (downloads the best one into a separate folder,\n'
            "leaving the video's files alone):\n"
            '  subliminal --debug download -l fr --force -d /tmp/test VIDEO'
        ),
        'cli.choose': 'interactive flow (kdialog windows): choose a subtitle and save it',
        'cli.choose_epilog': (
            'Same steps as "list" (all done by subliminal, with its configuration), then:\n'
            '  download_subtitles (chosen provider) and save_subtitles (name reserved first:\n'
            '  no existing file is ever overwritten).\n\n'
            'To see what happens, in a terminal:\n'
            '  subdolphin --debug choose VIDEO'
        ),
        'cli.auto': 'best subtitle for each video (files or folders), no questions, then a summary',
        'cli.auto_epilog': (
            'Does what "subliminal download" does, with the same configuration:\n'
            '  videos that already have subtitles are skipped (unless force,\n'
            '  force_external_subtitles, force_embedded_subtitles); choice by\n'
            '  download_best_subtitles (min_score, subtitle_categories, skip_wrong_fps), which\n'
            '  moves on to the next one if a download fails; saved without overwriting\n'
            '  (name reserved, then save_subtitles).\n'
            'In a folder, symbolic links are ignored (collect_video_filepaths).\n\n'
            'To see what happens, in a terminal:\n'
            '  subdolphin --debug auto --text PATH…\n\n'
            'Closest subliminal command (downloads into a separate folder):\n'
            '  subliminal --debug download -l fr -d /tmp/test PATH…'
        ),
        'cli.menu': 'install or remove the "Subtitles" submenu of Dolphin\'s context menu',
        'cli.menu_action': 'install (or update); remove',
        'cli.menu_epilog': (
            'Two files in ~/.local/share/kio/servicemenus/ (executable, as KDE requires):\n'
            '  subdolphin-choose.desktop: "Choose a subtitle…", a single video;\n'
            '  subdolphin-auto.desktop: "Best subtitle automatically", videos and folders.\n'
            'They run the subdolphin command used to install them (absolute path).'
        ),
        'cli.video': 'video to analyse',
        'cli.paths': 'videos or folders',
        'cli.title': 'title to use instead of the file name, e.g. "The Fall (2006)"',
        'cli.count': 'number of candidates shown (default: {n})',
        'cli.count_all': 'number of candidates shown (default: all)',
        'cli.json': 'JSON output',
        'cli.text': 'in the terminal, without windows',
        'err.config_toml': 'Unreadable configuration ({path}): {error}',
        'err.config_language': 'No language in [download] language of {path}',
        'err.config_name': 'Invalid name pattern in [download] name of {path}: {error}',
        'err.video': 'Unusable video: {error}',
        'err.kdialog': 'kdialog not found: it displays the windows of "choose".',
        'list.video': 'Video: {name}',
        'list.guessit_name': 'Analysed name: {name}',
        'list.movie': 'Recognised: movie "{title}"',
        'list.episode': 'Recognised: episode "{title}"',
        'list.unrecognized': 'Title not recognised: run again with --title "Title (year)"',
        'list.embedded': 'Embedded tracks:',
        'list.embedded_none': 'Embedded tracks: none',
        'list.external': 'Already present:',
        'list.external_none': 'Already present: none',
        'list.none': 'No subtitle found.',
        'list.header': '  #  Score     ★  Source            HI  MT  fps     Version',
        'list.total': '{n} candidate(s) found, {shown} shown.',
        'list.total_threshold': '{n} candidate(s) found, {kept} at {threshold}% or more; {shown} shown.',
        'list.legend': '★: hash match (sync guaranteed); HI: hearing impaired; MT: machine translated',
        'mark.machine_translated': 'MT',
        'kind.text': 'text',
        'kind.image': 'image',
        'kind.unknown': 'unknown kind',
        'track.forced': 'forced',
        'track.hearing_impaired': 'hearing impaired',
        'language.unknown': 'unknown language',
        'language.fr': 'French',
        'language.en': 'English',
        'ui.title': 'Subtitles',
        'ui.video_error': 'Unusable video: {error}',
        'ui.read_only': 'Cannot write to "{folder}": no subtitle could be saved there.',
        'ui.title_not_found': (
            'Title not recognised for "{name}".\n\n'
            'Title to search for (movie: "Title (year)"; episode: "Series S01E02"):'
        ),
        'ui.still_not_found': (
            '"{title}" is not recognised.\n\n'
            'Title to search for (movie: "Title (year)"; episode: "Series S01E02"):'
        ),
        'ui.correct_title': 'Title to search for (movie: "Title (year)"; episode: "Series S01E02"):',
        'ui.searching': 'Searching subtitles for "{title}"…',
        'ui.none_found': '"{title}": no subtitle found.',
        'ui.found': '"{title}": {n} subtitle(s) found',
        'ui.found_threshold': '"{title}": {n} subtitle(s) found, {kept} at {threshold}% or more',
        'ui.order_all': ', from best to worst.',
        'ui.order_limited': '; here are the {shown} best.',
        'ui.present': 'Already present: {items}',
        'ui.embedded': 'Embedded tracks: {items}',
        'ui.legend': '★ sync guaranteed · HI hearing impaired · MT machine translated',
        'ui.line_correct': '↻ Correct the title and search again…',
        'ui.line_options': '⚙ Options for this search: {summary}…',
        'ui.options_summary': 'languages {languages} · {categories}',
        'ui.all_categories': 'all categories',
        'ui.options': 'Options for this search only (nothing is saved;\nstarting values: subliminal.toml):',
        'ui.option_language': 'Language: {name}',
        'ui.category_n': 'Regular subtitles',
        'ui.category_hi': 'Hearing impaired (HI)',
        'ui.category_fo': 'Forced (foreign-language parts only)',
        'ui.category_short_n': 'regular',
        'ui.category_short_hi': 'HI',
        'ui.category_short_fo': 'forced',
        'ui.options_incomplete': 'At least one language and one category are needed: options unchanged.',
        'ui.fps': '{fps} fps',
        'ui.downloading': 'Downloading from {provider}…',
        'ui.download_failed': (
            'Downloading from {provider} failed.\n\n'
            'To see why, in a terminal:\n'
            'subdolphin --debug choose "{path}"'
        ),
        'ui.duplicate': 'This subtitle is identical to "{name}", already present: it was not created again.',
        'ui.save_error': 'Saving failed: {error}',
        'ui.saved': 'Saved: {name}',
        'auto.start': 'Automatic subtitles: {n} video(s)…',
        'auto.video': 'Video {index} / {total}: {name}',
        'auto.read_only': 'read-only folder',
        'auto.summary_title': 'Automatic subtitles: {n} video(s)',
        'auto.no_video': 'No video found.\n(In a folder, symbolic links are ignored, as subliminal does.)',
        'auto.saved': 'Saved: {n}',
        'auto.already_have': 'Already have subtitles, skipped: {n}',
        'auto.nothing_found': 'Nothing found at {threshold}% or more: {n}',
        'auto.nothing_found_no_threshold': 'Nothing found: {n}',
        'auto.unrecognized': 'Title not recognised (use "Choose a subtitle…"): {n}',
        'auto.duplicates': 'Identical to a subtitle already present: {n}',
        'auto.errors': 'Errors: {n}',
        'auto.error_line': '    {name}: {error}',
        'auto.more': '… and {n} more',
        'auto.cancelled': 'Cancelled after {done} of {total} video(s).',
        'auto.help': 'For details, in a terminal: subdolphin --debug auto --text PATH…',
        'menu.installed': '"Subtitles" menu installed; it runs: {command}',
        'menu.removed': '"Subtitles" menu removed.',
        'menu.none': 'No subdolphin menu to remove.',
    },
}


def ui_language() -> str:
    """Interface language: French if the system is in French, English otherwise."""
    for variable in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        value = os.environ.get(variable)
        if value:
            return 'fr' if value.split(':')[0].lower().startswith('fr') else 'en'
    return 'en'


def t(key: str, **params: object) -> str:
    """Text `key` in the interface language."""
    return TEXTS[ui_language()][key].format(**params)


def t_or(key: str, default: str) -> str:
    """Text `key` if it exists, `default` otherwise (e.g. the name of a language without translation)."""
    return TEXTS[ui_language()].get(key, default)


def percent(value: float) -> str:
    """Percentage with one decimal, with the typography of the interface language."""
    if ui_language() == 'fr':
        return f'{value:.1f} %'.replace('.', ',')
    return f'{value:.1f}%'
