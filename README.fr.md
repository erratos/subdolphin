# subdolphin

*[English version](README.md)*

Des sous-titres depuis le clic droit de Dolphin, avec [subliminal](https://github.com/Diaoul/subliminal).

subdolphin ajoute un sous-menu **Sous-titres** à Dolphin (KDE Plasma 6) :

- **Choisir un sous-titre…** (une vidéo) : affiche tous les sous-titres trouvés par subliminal, du
  meilleur au moins bon, et vous laisse choisir, même si la vidéo en a déjà (ceux qui sont là ne
  conviennent peut-être pas).
- **Meilleur sous-titre automatique** (vidéos et/ou dossiers) : fait ce que fait `subliminal download`
  avec la même configuration, puis affiche un bilan.

subdolphin est une fine couche autour de subliminal : recherche, score, téléchargement et
configuration sont ceux de subliminal (même `subliminal.toml`). subdolphin ajoute les fenêtres (kdialog)
et quelques règles :

- il **n'écrase jamais** un fichier : `Film.fr.srt`, puis `Film.<source>.fr.srt`, `Film.<source>-2.fr.srt`… ;
- il n'enregistre pas un sous-titre identique à un sous-titre déjà présent à côté de la vidéo ;
- il montre ce qui est déjà là : fichiers de sous-titres, pistes intégrées (texte ou image, forcées,
  pour malentendants).

## Prérequis

- Linux avec KDE Plasma 6 et Dolphin (KIO 6), `kdialog`, `qdbus6` (ou `qdbus`).
- Python ≥ 3.11 et [uv](https://docs.astral.sh/uv/).
- Un fichier de configuration de subliminal, `~/.config/subliminal/subliminal.toml`, avec au moins une
  langue (voir [Configuration](#configuration)). subliminal (2.7.x) est installé comme dépendance.

## Installation

```bash
uv tool install git+https://github.com/erratos/subdolphin
subdolphin menu installer
```

- Si vous utilisez aussi la commande `subliminal`, installez les deux avec **le même Python**
  (`--python`, par exemple `--python /usr/bin/python3.14`) : elles partagent un cache dont le format de
  fichier dépend de Python (voir [Dépannage](#dépannage)).
- `subdolphin menu installer` écrit deux menus de service dans `~/.local/share/kio/servicemenus/`
  (exécutables, comme KDE l'exige). Ils lancent la commande `subdolphin` qui les a installés, par son
  chemin absolu : relancez-la si la commande change de place.
- Redémarrez Dolphin si le menu n'apparaît pas.

## Utilisation

### Dans Dolphin

**Clic droit sur une vidéo → Sous-titres → Choisir un sous-titre…**

1. Une fenêtre montre le titre reconnu (en gras), ce qui est déjà là, puis :
   - **↻ Corriger le titre et relancer la recherche…** ;
   - **⚙ Options de cette recherche** : langues et catégories (normaux, malentendants, forcés), pour
     cette recherche seulement ; valeurs de départ : `subliminal.toml`, rien n'est enregistré ;
   - tous les sous-titres à `min_score` ou plus, du meilleur au moins bon : score, ★ (empreinte :
     synchro assurée), source, nom de la version, `HI` (malentendants), `TA` (traduction automatique),
     images par seconde.
2. Sélectionnez une ligne et validez par OK (les listes de kdialog ne gèrent pas le double-clic).
3. Le sous-titre est téléchargé et enregistré à côté de la vidéo ; une notification donne son nom.

Si le titre n'est pas reconnu, il vous est demandé : `Titre (année)` pour un film, `Série S01E02` pour
un épisode.

**Clic droit sur des vidéos et/ou des dossiers → Sous-titres → Meilleur sous-titre automatique**

- Les dossiers sont parcourus avec leurs sous-dossiers ; les dossiers cachés, les fichiers et dossiers
  `sample` et les liens symboliques trouvés dans les dossiers sont ignorés, comme le fait subliminal.
- Les vidéos qui ont déjà un sous-titre dans la langue voulue (fichier ou piste intégrée) sont sautées,
  sauf réglage `force` (voir plus bas).
- Une barre de progression (avec Annuler), puis un bilan : enregistrés, déjà pourvues, rien trouvé, titre
  non reconnu, identiques à un sous-titre présent, erreurs.

### En ligne de commande

L'interface suit la langue du système (français ou anglais).

```bash
subdolphin liste VIDÉO [--titre "Titre (année)"] [-n N] [--json]  # recherche seule, rien n'est téléchargé
subdolphin choisir VIDÉO                                          # « Choisir un sous-titre… » (fenêtres)
subdolphin auto CHEMIN… [--texte]                                 # automatique ; --texte : dans le terminal
subdolphin menu installer | retirer                               # installer / retirer le menu de Dolphin
subdolphin --debug …                                              # afficher le journal de subliminal
subdolphin --config FICHIER …                                     # un autre subliminal.toml
```

`subdolphin COMMANDE --help` décrit chaque étape en termes de subliminal, avec la commande `subliminal`
la plus proche.

## Configuration

subdolphin n'a pas de configuration propre : il lit celle de subliminal
(`~/.config/subliminal/subliminal.toml`), avec les mêmes règles que la commande `subliminal`.

| Réglage (`[download]` sauf indication) | Effet dans subdolphin |
|---|---|
| `language` | langues recherchées (obligatoire) |
| `provider`, `extend_provider`, `ignore_provider` | sources utilisées |
| `refiner`, `extend_refiner`, `ignore_refiner` | refiners utilisés |
| `name` | substitutions à la sed du nom passé à guessit (voir les pièges) |
| `min_score` | seuil, en % du score maximum, pour la liste et le mode automatique |
| `subtitle_categories` | ex. `"n,fo"` : normaux et forcés, sans malentendants ; `"fo"` : forcés seulement |
| `skip_wrong_fps` | mode automatique : écarter les sous-titres dont les images par seconde diffèrent |
| `force`, `force_external_subtitles`, `force_embedded_subtitles` | mode automatique : télécharger même si la langue est déjà là |
| `encoding`, `subtitle_format`, `language_format` | écriture des sous-titres (UTF-8 par défaut) |
| `max_workers` | sources interrogées en parallèle |
| `[provider.*]`, `[refiner.*]` | identifiants et options |
| `[default] cache_dir` | cache, partagé avec la commande `subliminal` |

Exemple avec les réglages conseillés (voir les pièges ci-dessous) :

```toml
[download]
language = ["fr"]
min_score = 50
subtitle_categories = "n,fo"
name = ['s|^/run/media/[^/]+/[^/]+/||']
ignore_refiner = ["omdb"]
ignore_provider = ["podnapisi"]

[provider.opensubtitlescom]
username = "votre-pseudo"   # le pseudo, pas l'adresse e-mail
password = "…"
max_result_pages = 10

[provider.addic7ed]
username = "…"
password = "…"

[refiner.tmdb]
apikey = "…"                # clé d'API TMDB (v3)
```

Le fichier contient des mots de passe et des clés : gardez-le privé (`chmod 600`).

### Pièges (subliminal 2.7.1)

- **guessit lit le chemin complet.** Un point de montage comme `/run/media/user/Nom du disque/…` peut être
  pris pour le titre, et faire d'un film un « épisode ». subdolphin retire par défaut
  `/run/media/<user>/<disque>/` et `/media/<user>/<disque>/`, après vos propres motifs `name`.
- **OMDb** retient le premier résultat de la bonne année, qui peut être un autre film du même titre ; le
  mauvais identifiant IMDb favorise alors les mauvais sous-titres. Préférez TMDB :
  `ignore_refiner = ["omdb"]`.
- **OpenSubtitles.com pagine sans limite** : une recherche par titre seul peut atteindre la page 21,
  recevoir une erreur HTTP 400 et perdre tous ses résultats. Réglez `max_result_pages = 10`.
- **OpenSubtitles.com** se connecte avec le *pseudo*, pas l'adresse e-mail, et seulement au téléchargement.
- **OpenSubtitles.com n'utilise l'empreinte de la vidéo que si la source `opensubtitles` est aussi
  active** (corrigé dans subliminal après la 2.7.1,
  [#1382](https://github.com/Diaoul/subliminal/issues/1382)) : ne l'ignorez pas.
- **addic7ed, gestdown et tvsubtitles ne traitent que les épisodes**, jamais les films.
- **podnapisi** était injoignable au moment de la rédaction (octobre 2026).

## Noms des fichiers enregistrés

| Situation | Nom |
|---|---|
| encore aucun sous-titre dans cette langue | `Film.fr.srt` (`Film.fr.hi.srt` pour malentendants) |
| il y en a déjà un | `Film.<source>.fr.srt`, ex. `Film.opensubtitlescom.fr.srt` |
| ce nom est pris | `Film.<source>-2.fr.srt`, `-3`… |

mpv ne reconnaît la langue que si elle termine le nom (éventuellement suivie de `hi`, `sdh` ou
`forced`) ; le suffixe `[hi]` de subliminal n'est pas compris par mpv, d'où `.fr.hi`. Le nom est réservé
avant l'écriture (création exclusive) : rien n'est jamais écrasé, même par deux lancements simultanés.

subliminal lui-même ne reconnaît que les noms du type `Film.fr.srt` : pour lui, `Film.<source>.fr.srt` est
de langue indéterminée. Le mode automatique peut donc ajouter plus tard un `Film.fr.srt`, sans rien écraser.

## Dépannage

- **Voir ce qui se passe** : lancez `subdolphin --debug choisir VIDÉO` (ou `liste`, ou `auto --texte`)
  dans un terminal. Comme `subliminal --debug`, le journal peut afficher un jeton de session
  OpenSubtitles.org : ne le publiez pas.
- **Commande `subliminal` la plus proche** (télécharge dans un dossier à part, sans toucher aux fichiers
  de la vidéo) : `subliminal --debug download -l fr --force -d /tmp/essai VIDÉO`.
- **« Le téléchargement depuis opensubtitlescom a échoué » alors que le quota va bien** : vérifiez que
  `subliminal` et `subdolphin` tournent sur le même Python. Le cache partagé
  (`~/.cache/subliminal/subliminal.dbm*`) est un fichier dbm dont le format dépend de Python : Python 3.13+
  crée des fichiers à base de SQLite que Python 3.12 ne sait pas lire, et l'inverse arrive aussi.
  subliminal ignore les erreurs de cache sans rien dire, ce qui empêche la connexion à OpenSubtitles.com
  (son jeton est gardé dans le cache) et les recherches TMDB. Correction : réinstaller les deux outils avec
  le même `--python`, puis supprimer l'ancien fichier de cache ; il se reconstruit tout seul.
- **Pas de menu** : relancez `subdolphin menu installer` et redémarrez Dolphin. Le menu n'apparaît que sur
  des fichiers locaux : « Choisir… » pour une seule vidéo, « Meilleur sous-titre automatique » pour des
  vidéos et des dossiers ; il est masqué si la sélection contient d'autres fichiers.

## Mise à jour et désinstallation

```bash
uv tool install --reinstall git+https://github.com/erratos/subdolphin   # avec le même --python qu'avant
subdolphin menu retirer
uv tool uninstall subdolphin
```

## Développement

```bash
git clone https://github.com/erratos/subdolphin
cd subdolphin
uv sync
uv run pytest
uv run subdolphin liste VIDÉO
```

Les tests n'utilisent jamais le réseau (il est bloqué dans `tests/conftest.py`). Organisation de
`src/subdolphin/` :

| Module | Rôle |
|---|---|
| `config.py` | lit `subliminal.toml` avec les règles de la ligne de commande de subliminal |
| `analyse.py` | reconnaît la vidéo (`scan_video`), pistes intégrées, sous-titres présents |
| `recherche.py` | refiners, liste des candidats, scores, seuil, téléchargement |
| `enregistrement.py` | noms de fichiers, doublons, écriture sans écrasement |
| `parcours.py` | parcours « Choisir un sous-titre… », indépendant des fenêtres |
| `auto.py` | mode automatique |
| `ui_kdialog.py`, `ui_terminal.py` | fenêtres kdialog, affichage dans le terminal |
| `menu.py` | menus de service de Dolphin |
| `textes.py` | textes de l'interface (français, anglais) |
| `cli.py` | ligne de commande |

## Licence

[MIT](LICENSE), comme subliminal.
