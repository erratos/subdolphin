"""Textes de l'interface (français, anglais), choisis selon la langue du système."""

from __future__ import annotations

import os

TEXTES: dict[str, dict[str, str]] = {
    'fr': {
        'cli.description': 'Sous-titres depuis le clic droit de Dolphin, avec subliminal.',
        'cli.config': 'fichier de configuration de subliminal (par défaut : {chemin})',
        'cli.debug': 'affiche le journal de subliminal (comme `subliminal --debug`)',
        'cli.liste': 'affiche les meilleurs sous-titres trouvés pour une vidéo, sans rien télécharger',
        'cli.liste_epilogue': (
            'Toutes les étapes sont faites par subliminal, avec sa configuration :\n'
            '  scan_video (nom passé à guessit : [download] name), refiners (metadata, hash, tmdb…),\n'
            '  AsyncProviderPool.list_subtitles, puis tri de download_best_subtitles\n'
            '  (subtitle_categories, puis compute_score).\n\n'
            'Pour voir ce qui se passe :\n'
            '  subdolphin --debug liste VIDÉO\n\n'
            'Commande subliminal la plus proche (télécharge le meilleur dans un dossier à part,\n'
            'sans toucher aux fichiers de la vidéo) :\n'
            '  subliminal --debug download -l fr --force -d /tmp/essai VIDÉO'
        ),
        'cli.choisir': 'parcours interactif (fenêtres kdialog) : choisir un sous-titre et l\'enregistrer',
        'cli.choisir_epilogue': (
            'Mêmes étapes que « liste » (toutes faites par subliminal, avec sa configuration), puis :\n'
            '  download_subtitles (source choisie) et save_subtitles (nom réservé d\'abord :\n'
            '  aucun fichier existant n\'est jamais écrasé).\n\n'
            'Pour voir ce qui se passe, dans un terminal :\n'
            '  subdolphin --debug choisir VIDÉO'
        ),
        'ui.titre': 'Sous-titres',
        'ui.erreur_video': 'Vidéo inutilisable : {erreur}',
        'ui.dossier_protege': 'Impossible d\'écrire dans « {dossier} » : aucun sous-titre ne pourrait y être enregistré.',
        'ui.titre_introuvable': (
            'Titre non reconnu pour « {nom} ».\n\n'
            'Titre à rechercher (film : « Titre (année) » ; épisode : « Série S01E02 ») :'
        ),
        'ui.toujours_introuvable': (
            '« {titre} » n\'est pas reconnu.\n\n'
            'Titre à rechercher (film : « Titre (année) » ; épisode : « Série S01E02 ») :'
        ),
        'ui.titre_corriger': 'Titre à rechercher (film : « Titre (année) » ; épisode : « Série S01E02 ») :',
        'ui.recherche': 'Recherche des sous-titres pour « {titre} »…',
        'ui.aucun_trouve': '« {titre} » : aucun sous-titre trouvé.',
        'ui.trouves': '« {titre} » : {n} sous-titre(s) trouvé(s)',
        'ui.trouves_seuil': '« {titre} » : {n} sous-titre(s) trouvé(s), dont {retenus} à {seuil} % ou plus',
        'ui.ordre_tous': ', du meilleur au moins bon.',
        'ui.ordre_limite': ' ; voici les {affiches} meilleurs.',
        'ui.liste_presents': 'Déjà présents : {liste}',
        'ui.liste_pistes': 'Pistes intégrées : {liste}',
        'ui.liste_legende': '★ synchro assurée · HI malentendants · TA traduction automatique',
        'ui.ligne_corriger': '↻ Corriger le titre et relancer la recherche…',
        'ui.ligne_options': '⚙ Options de cette recherche : {resume}…',
        'ui.resume_options': 'langues {langues} · {categories}',
        'ui.categories_toutes': 'toutes catégories',
        'ui.options': (
            'Options de cette recherche seulement (rien n\'est enregistré ;\n'
            'valeurs de départ : subliminal.toml) :'
        ),
        'ui.option_langue': 'Langue : {nom}',
        'ui.categorie_n': 'Sous-titres normaux',
        'ui.categorie_hi': 'Malentendants (HI)',
        'ui.categorie_fo': 'Forcés (passages en langue étrangère seulement)',
        'ui.categorie_court_n': 'normaux',
        'ui.categorie_court_hi': 'HI',
        'ui.categorie_court_fo': 'forcés',
        'ui.options_incompletes': 'Il faut au moins une langue et une catégorie : options inchangées.',
        'langue.fr': 'français',
        'langue.en': 'anglais',
        'ui.fps': '{fps} i/s',
        'ui.telechargement': 'Téléchargement depuis {source}…',
        'ui.echec_telechargement': (
            'Le téléchargement depuis {source} a échoué.\n\n'
            'Pour voir pourquoi, dans un terminal :\n'
            'subdolphin --debug choisir "{chemin}"'
        ),
        'ui.doublon': 'Ce sous-titre est identique à « {nom} », déjà présent : il n\'a pas été recréé.',
        'ui.erreur_ecriture': 'Échec de l\'enregistrement : {erreur}',
        'ui.enregistre': 'Enregistré : {nom}',
        'err.kdialog': 'kdialog est introuvable : il sert à afficher les fenêtres de « choisir ».',
        'cli.auto': 'meilleur sous-titre pour chaque vidéo (fichiers ou dossiers), sans question, puis bilan',
        'cli.auto_epilogue': (
            'Fait ce que fait « subliminal download » avec la même configuration :\n'
            '  vidéos déjà pourvues sautées (sauf force, force_external_subtitles,\n'
            '  force_embedded_subtitles) ; choix par download_best_subtitles (min_score,\n'
            '  subtitle_categories, skip_wrong_fps), qui passe au suivant si un téléchargement\n'
            '  échoue ; enregistrement sans écraser (nom réservé, puis save_subtitles).\n'
            'Dans un dossier, les liens symboliques sont ignorés (collect_video_filepaths).\n\n'
            'Pour voir ce qui se passe, dans un terminal :\n'
            '  subdolphin --debug auto --texte CHEMIN…\n\n'
            'Commande subliminal la plus proche (télécharge dans un dossier à part) :\n'
            '  subliminal --debug download -l fr -d /tmp/essai CHEMIN…'
        ),
        'cli.chemins': 'vidéos ou dossiers',
        'cli.texte': 'dans le terminal, sans fenêtre',
        'auto.debut': 'Sous-titres automatiques : {n} vidéo(s)…',
        'auto.video': 'Vidéo {rang} / {total} : {nom}',
        'auto.lecture_seule': 'dossier en lecture seule',
        'auto.bilan_titre': 'Sous-titres automatiques : {n} vidéo(s)',
        'auto.aucune_video': (
            'Aucune vidéo trouvée.\n'
            '(Dans un dossier, les liens symboliques sont ignorés, comme par subliminal.)'
        ),
        'auto.enregistres': 'Enregistrés : {n}',
        'auto.deja_pourvues': 'Déjà pourvues, sautées : {n}',
        'auto.rien_trouve': 'Rien trouvé à {seuil} % ou plus : {n}',
        'auto.rien_trouve_sans_seuil': 'Rien trouvé : {n}',
        'auto.non_reconnues': 'Titre non reconnu (utiliser « Choisir… ») : {n}',
        'auto.doublons': 'Identiques à un sous-titre déjà présent : {n}',
        'auto.erreurs': 'Erreurs : {n}',
        'auto.autres': '… et {n} autre(s)',
        'auto.annule': 'Annulé après {fait} vidéo(s) sur {total}.',
        'auto.aide': 'Pour le détail, dans un terminal : subdolphin --debug auto --texte CHEMIN…',
        'cli.menu': 'installe ou retire le sous-menu « Sous-titres » du clic droit de Dolphin',
        'cli.menu_action': 'installer (ou mettre à jour) ; retirer',
        'cli.menu_epilogue': (
            'Deux fichiers dans ~/.local/share/kio/servicemenus/ (exécutables, comme KDE l\'exige) :\n'
            '  subdolphin-choisir.desktop : « Choisir un sous-titre… », une seule vidéo ;\n'
            '  subdolphin-auto.desktop : « Meilleur sous-titre automatique », vidéos et dossiers.\n'
            'Ils lancent la commande subdolphin utilisée pour les installer (chemin absolu).'
        ),
        'menu.installe': 'Menu « Sous-titres » installé ; il lance : {commande}',
        'menu.retire': 'Menu « Sous-titres » retiré.',
        'menu.absent': 'Aucun menu de subdolphin à retirer.',
        'cli.fichier': 'vidéo à analyser',
        'cli.titre': 'titre à utiliser à la place du nom de fichier, ex. « The Fall (2006) »',
        'cli.nombre': 'nombre de candidats affichés (défaut : {n})',
        'cli.nombre_tous': 'nombre de candidats affichés (défaut : tous)',
        'cli.json': 'sortie JSON',
        'err.config_toml': 'Configuration illisible ({chemin}) : {erreur}',
        'err.config_langue': 'Aucune langue dans [download] language de {chemin}',
        'err.config_nom': 'Motif de nom incorrect dans [download] name de {chemin} : {erreur}',
        'err.video': 'Vidéo inutilisable : {erreur}',
        'liste.video': 'Vidéo : {nom}',
        'liste.film': 'Reconnu : film « {titre} »',
        'liste.episode': 'Reconnu : épisode « {titre} »',
        'liste.non_reconnu': 'Titre non reconnu : relancer avec --titre "Titre (année)"',
        'liste.nom_analyse': 'Nom analysé : {nom}',
        'liste.pistes': 'Pistes intégrées :',
        'liste.pistes_aucune': 'Pistes intégrées : aucune',
        'liste.externes': 'Déjà présents :',
        'liste.externes_aucun': 'Déjà présents : aucun',
        'liste.aucun': 'Aucun sous-titre trouvé.',
        'liste.total': '{n} candidat(s) trouvé(s), {affiches} affiché(s).',
        'liste.total_seuil': '{n} candidat(s) trouvé(s), dont {retenus} à {seuil} % ou plus ; {affiches} affiché(s).',
        'liste.entete': '  #  Score     ★  Source            HI  TA  fps     Version',
        'liste.legende': '★ : empreinte (synchro assurée) ; HI : malentendants ; TA : traduction automatique',
        'nature.texte': 'texte',
        'nature.image': 'image',
        'nature.inconnue': 'nature inconnue',
        'piste.forcee': 'forcé',
        'piste.malentendants': 'malentendants',
        'langue.inconnue': 'langue inconnue',
    },
    'en': {
        'cli.description': "Subtitles from Dolphin's context menu, with subliminal.",
        'cli.config': 'subliminal configuration file (default: {chemin})',
        'cli.debug': "show subliminal's log (like `subliminal --debug`)",
        'cli.liste': 'show the best subtitles found for a video, without downloading anything',
        'cli.liste_epilogue': (
            'Every step is done by subliminal, with its configuration:\n'
            '  scan_video (name passed to guessit: [download] name), refiners (metadata, hash, tmdb…),\n'
            '  AsyncProviderPool.list_subtitles, then the download_best_subtitles ordering\n'
            '  (subtitle_categories, then compute_score).\n\n'
            'To see what happens:\n'
            '  subdolphin --debug liste VIDEO\n\n'
            'Closest subliminal command (downloads the best one into a separate folder,\n'
            "leaving the video's files alone):\n"
            '  subliminal --debug download -l fr --force -d /tmp/test VIDEO'
        ),
        'cli.choisir': 'interactive flow (kdialog windows): choose a subtitle and save it',
        'cli.choisir_epilogue': (
            'Same steps as "liste" (all done by subliminal, with its configuration), then:\n'
            '  download_subtitles (chosen source) and save_subtitles (name reserved first:\n'
            '  no existing file is ever overwritten).\n\n'
            'To see what happens, in a terminal:\n'
            '  subdolphin --debug choisir VIDEO'
        ),
        'ui.titre': 'Subtitles',
        'ui.erreur_video': 'Unusable video: {erreur}',
        'ui.dossier_protege': 'Cannot write to "{dossier}": no subtitle could be saved there.',
        'ui.titre_introuvable': (
            'Title not recognised for "{nom}".\n\n'
            'Title to search for (movie: "Title (year)"; episode: "Series S01E02"):'
        ),
        'ui.toujours_introuvable': (
            '"{titre}" is not recognised.\n\n'
            'Title to search for (movie: "Title (year)"; episode: "Series S01E02"):'
        ),
        'ui.titre_corriger': 'Title to search for (movie: "Title (year)"; episode: "Series S01E02"):',
        'ui.recherche': 'Searching subtitles for "{titre}"…',
        'ui.aucun_trouve': '"{titre}": no subtitle found.',
        'ui.trouves': '"{titre}": {n} subtitle(s) found',
        'ui.trouves_seuil': '"{titre}": {n} subtitle(s) found, {retenus} at {seuil}% or more',
        'ui.ordre_tous': ', from best to worst.',
        'ui.ordre_limite': '; here are the {affiches} best.',
        'ui.liste_presents': 'Already present: {liste}',
        'ui.liste_pistes': 'Embedded tracks: {liste}',
        'ui.liste_legende': '★ sync guaranteed · HI hearing impaired · MT machine translated',
        'ui.ligne_corriger': '↻ Correct the title and search again…',
        'ui.ligne_options': '⚙ Options for this search: {resume}…',
        'ui.resume_options': 'languages {langues} · {categories}',
        'ui.categories_toutes': 'all categories',
        'ui.options': 'Options for this search only (nothing is saved;\nstarting values: subliminal.toml):',
        'ui.option_langue': 'Language: {nom}',
        'ui.categorie_n': 'Regular subtitles',
        'ui.categorie_hi': 'Hearing impaired (HI)',
        'ui.categorie_fo': 'Forced (foreign-language parts only)',
        'ui.categorie_court_n': 'regular',
        'ui.categorie_court_hi': 'HI',
        'ui.categorie_court_fo': 'forced',
        'ui.options_incompletes': 'At least one language and one category are needed: options unchanged.',
        'langue.fr': 'French',
        'langue.en': 'English',
        'ui.fps': '{fps} fps',
        'ui.telechargement': 'Downloading from {source}…',
        'ui.echec_telechargement': (
            'Downloading from {source} failed.\n\n'
            'To see why, in a terminal:\n'
            'subdolphin --debug choisir "{chemin}"'
        ),
        'ui.doublon': 'This subtitle is identical to "{nom}", already present: it was not created again.',
        'ui.erreur_ecriture': 'Saving failed: {erreur}',
        'ui.enregistre': 'Saved: {nom}',
        'err.kdialog': 'kdialog not found: it displays the windows of "choisir".',
        'cli.auto': 'best subtitle for each video (files or folders), no questions, then a summary',
        'cli.auto_epilogue': (
            'Does what "subliminal download" does, with the same configuration:\n'
            '  videos that already have subtitles are skipped (unless force,\n'
            '  force_external_subtitles, force_embedded_subtitles); choice by\n'
            '  download_best_subtitles (min_score, subtitle_categories, skip_wrong_fps), which\n'
            '  moves on to the next one if a download fails; saved without overwriting\n'
            '  (name reserved, then save_subtitles).\n'
            'In a folder, symbolic links are ignored (collect_video_filepaths).\n\n'
            'To see what happens, in a terminal:\n'
            '  subdolphin --debug auto --texte PATH…\n\n'
            'Closest subliminal command (downloads into a separate folder):\n'
            '  subliminal --debug download -l fr -d /tmp/test PATH…'
        ),
        'cli.chemins': 'videos or folders',
        'cli.texte': 'in the terminal, without windows',
        'auto.debut': 'Automatic subtitles: {n} video(s)…',
        'auto.video': 'Video {rang} / {total}: {nom}',
        'auto.lecture_seule': 'read-only folder',
        'auto.bilan_titre': 'Automatic subtitles: {n} video(s)',
        'auto.aucune_video': 'No video found.\n(In a folder, symbolic links are ignored, as subliminal does.)',
        'auto.enregistres': 'Saved: {n}',
        'auto.deja_pourvues': 'Already have subtitles, skipped: {n}',
        'auto.rien_trouve': 'Nothing found at {seuil}% or more: {n}',
        'auto.rien_trouve_sans_seuil': 'Nothing found: {n}',
        'auto.non_reconnues': 'Title not recognised (use "Choisir…"): {n}',
        'auto.doublons': 'Identical to a subtitle already present: {n}',
        'auto.erreurs': 'Errors: {n}',
        'auto.autres': '… and {n} more',
        'auto.annule': 'Cancelled after {fait} of {total} video(s).',
        'auto.aide': 'For details, in a terminal: subdolphin --debug auto --texte PATH…',
        'cli.menu': 'install or remove the "Subtitles" submenu of Dolphin\'s context menu',
        'cli.menu_action': 'installer (install or update); retirer (remove)',
        'cli.menu_epilogue': (
            'Two files in ~/.local/share/kio/servicemenus/ (executable, as KDE requires):\n'
            '  subdolphin-choisir.desktop: "Choose a subtitle…", a single video;\n'
            '  subdolphin-auto.desktop: "Best subtitle automatically", videos and folders.\n'
            'They run the subdolphin command used to install them (absolute path).'
        ),
        'menu.installe': '"Subtitles" menu installed; it runs: {commande}',
        'menu.retire': '"Subtitles" menu removed.',
        'menu.absent': 'No subdolphin menu to remove.',
        'cli.fichier': 'video to analyse',
        'cli.titre': 'title to use instead of the file name, e.g. "The Fall (2006)"',
        'cli.nombre': 'number of candidates shown (default: {n})',
        'cli.nombre_tous': 'number of candidates shown (default: all)',
        'cli.json': 'JSON output',
        'err.config_toml': 'Unreadable configuration ({chemin}): {erreur}',
        'err.config_langue': 'No language in [download] language of {chemin}',
        'err.config_nom': 'Invalid name pattern in [download] name of {chemin}: {erreur}',
        'err.video': 'Unusable video: {erreur}',
        'liste.video': 'Video: {nom}',
        'liste.film': 'Recognised: movie "{titre}"',
        'liste.episode': 'Recognised: episode "{titre}"',
        'liste.non_reconnu': 'Title not recognised: run again with --titre "Title (year)"',
        'liste.nom_analyse': 'Analysed name: {nom}',
        'liste.pistes': 'Embedded tracks:',
        'liste.pistes_aucune': 'Embedded tracks: none',
        'liste.externes': 'Already present:',
        'liste.externes_aucun': 'Already present: none',
        'liste.aucun': 'No subtitle found.',
        'liste.total': '{n} candidate(s) found, {affiches} shown.',
        'liste.total_seuil': '{n} candidate(s) found, {retenus} at {seuil}% or more; {affiches} shown.',
        'liste.entete': '  #  Score     ★  Source            HI  MT  fps     Version',
        'liste.legende': '★: hash match (sync guaranteed); HI: hearing impaired; MT: machine translated',
        'nature.texte': 'text',
        'nature.image': 'image',
        'nature.inconnue': 'unknown kind',
        'piste.forcee': 'forced',
        'piste.malentendants': 'hearing impaired',
        'langue.inconnue': 'unknown language',
    },
}


def langue_interface() -> str:
    """Langue de l'interface : français si le système est en français, anglais sinon."""
    for variable in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        valeur = os.environ.get(variable)
        if valeur:
            return 'fr' if valeur.split(':')[0].lower().startswith('fr') else 'en'
    return 'en'


def t(cle: str, **parametres: object) -> str:
    """Texte `cle` dans la langue de l'interface."""
    return TEXTES[langue_interface()][cle].format(**parametres)


def t_ou(cle: str, defaut: str) -> str:
    """Texte `cle` s'il existe, sinon `defaut` (ex. nom d'une langue sans traduction)."""
    return TEXTES[langue_interface()].get(cle, defaut)


def pourcentage(valeur: float) -> str:
    """Pourcentage avec une décimale, à la typographie de la langue de l'interface."""
    if langue_interface() == 'fr':
        return f'{valeur:.1f} %'.replace('.', ',')
    return f'{valeur:.1f}%'
