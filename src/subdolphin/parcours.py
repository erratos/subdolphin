"""Parcours « Choisir un sous-titre… » (PLAN.md 5.2), indépendant des fenêtres (objet `ui`)."""

from __future__ import annotations

import html
from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from babelfish import Language
from subliminal.subtitle import Subtitle

from .analyse import Analyse, analyser, nature, titre_lisible
from .config import Config
from .enregistrement import dossier_inscriptible, enregistrer
from .recherche import Candidat, affiner, au_dessus, lister, telecharger
from .textes import pourcentage, t, t_ou

#: Étiquettes des deux premières lignes de la liste.
CORRIGER = 'corriger'
OPTIONS = 'options'

#: Langues toujours proposées dans les options, en plus de celles de la config.
LANGUES_PROPOSEES = ('fr', 'en')
#: Catégories de subliminal (`subtitle_categories`) : normaux, malentendants, forcés.
CATEGORIES = ('n', 'hi', 'fo')


class Interface(Protocol):
    """Ce que le parcours demande aux fenêtres (`ui_kdialog.Kdialog`, ou un faux pour les tests)."""

    def choisir(self, texte: str, choix: list[tuple[str, str]]) -> str | None: ...
    def cocher(self, texte: str, cases: list[tuple[str, str, bool]]) -> list[str] | None: ...
    def saisir(self, texte: str, defaut: str) -> str | None: ...
    def informer(self, texte: str) -> None: ...
    def erreur(self, texte: str) -> None: ...
    def notifier(self, texte: str) -> None: ...
    def attente(self, texte: str) -> AbstractContextManager[None]: ...


@dataclass
class Relance:
    """Nouvelle recherche demandée depuis la liste."""

    titre: str | None = None  # nouveau titre (None : le même)
    config: Config | None = None  # options de cette recherche (None : les mêmes)


# --- Textes de la liste ---------------------------------------------------------------------------


def decrire(sous_titre: Subtitle) -> str:
    """« fr, malentendants » : langue et catégorie d'un sous-titre déjà présent (fichier ou piste)."""
    details = [str(sous_titre.language) if sous_titre.language else t('langue.inconnue')]
    if sous_titre.hearing_impaired:
        details.append(t('piste.malentendants'))
    if sous_titre.foreign_only:
        details.append(t('piste.forcee'))
    return ', '.join(details)


def ligne(candidat: Candidat) -> str:
    """« 86,7 %  ★ opensubtitlescom — The.Fall.2006… · HI · 23.976 i/s »."""
    marques = [m for m, oui in (('HI', candidat.malentendants), ('TA', candidat.traduction_auto)) if oui]
    if candidat.fps:
        marques.append(t('ui.fps', fps=f'{candidat.fps:g}'))
    debut = f'{pourcentage(candidat.pourcentage)}  {"★ " if candidat.empreinte else ""}{candidat.source}'
    return ' · '.join([f'{debut} — {candidat.version}', *marques])


def nom_langue(langue: Language) -> str:
    return t_ou(f'langue.{langue}', langue.name)


def resume_options(config: Config) -> str:
    """« langues fr · toutes catégories »."""
    if config.categories:
        categories = ', '.join(t(f'ui.categorie_court_{c}') for c in config.categories.split(',') if c in CATEGORIES)
    else:
        categories = t('ui.categories_toutes')
    return t('ui.resume_options', langues=', '.join(sorted(str(lg) for lg in config.langues)), categories=categories)


def entete(analyse: Analyse, candidats: Sequence[Candidat], retenus: Sequence[Candidat], config: Config,
           nombre: int | None) -> str:  # fmt: skip
    """En-tête de la liste, en HTML (kdialog l'affiche en texte enrichi) : titre reconnu en gras."""
    assert analyse.video is not None
    titre = f'<b>{html.escape(titre_lisible(analyse.video))}</b>'
    if not candidats:
        premiere = t('ui.aucun_trouve', titre=titre)
    else:
        if config.min_score:
            premiere = t('ui.trouves_seuil', titre=titre, n=len(candidats), retenus=len(retenus), seuil=config.min_score)
        else:
            premiere = t('ui.trouves', titre=titre, n=len(candidats))
        if nombre is not None and nombre < len(retenus):
            premiere += t('ui.ordre_limite', affiches=nombre)
        else:
            premiere += t('ui.ordre_tous')
    lignes = [premiere]
    if analyse.externes:
        presents = ' ; '.join(f'{c.name} ({decrire(s)})' for c, s in analyse.externes.items())
        lignes.append(html.escape(t('ui.liste_presents', liste=presents)))
    if analyse.pistes:
        pistes = ' ; '.join(f'{decrire(p)}, {t(f"nature.{nature(p)}")}' for p in analyse.pistes)
        lignes.append(html.escape(t('ui.liste_pistes', liste=pistes)))
    lignes.append(html.escape(t('ui.liste_legende')))
    return '<br>'.join(lignes)


# --- Options de cette recherche ------------------------------------------------------------------


def demander_options(config: Config, ui: Interface) -> Config | None:
    """Langues et catégories pour cette recherche seulement (valeurs de départ : la config).

    Renvoie la config modifiée, ou None si rien ne change (annulé ou choix incomplet).
    """
    codes = sorted({*LANGUES_PROPOSEES, *(str(lg) for lg in config.langues)})
    cochees = set(config.categories.split(',')) if config.categories else set(CATEGORIES)
    cases = [(f'langue:{c}', t('ui.option_langue', nom=nom_langue(Language.fromietf(c))),
              Language.fromietf(c) in config.langues) for c in codes]  # fmt: skip
    cases += [(f'categorie:{c}', t(f'ui.categorie_{c}'), c in cochees) for c in CATEGORIES]
    reponse = ui.cocher(t('ui.options'), cases)
    if reponse is None:
        return None
    langues = frozenset(Language.fromietf(e.removeprefix('langue:')) for e in reponse if e.startswith('langue:'))
    categories = [c for c in CATEGORIES if f'categorie:{c}' in reponse]
    if not langues or not categories:
        ui.informer(t('ui.options_incompletes'))
        return None
    if len(categories) == len(CATEGORIES) and not config.categories:
        texte_categories = ''  # tout coché, comme au départ : ni filtre ni tri
    else:
        # Ordre de préférence de la config d'abord (subliminal trie dans cet ordre), puis les autres.
        ordre = [c for c in config.categories.split(',') if c in CATEGORIES] + list(CATEGORIES)
        texte_categories = ','.join(dict.fromkeys(c for c in ordre if c in categories))
    return replace(config, langues=langues, categories=texte_categories)


# --- Parcours ------------------------------------------------------------------------------------


def proposer(analyse: Analyse, candidats: list[Candidat], config: Config, ui: Interface,
             nombre: int | None) -> int | Relance:  # fmt: skip
    """Liste → téléchargement → enregistrement (étapes 4 à 6).

    Renvoie un code de sortie, ou la nouvelle recherche demandée (titre corrigé, options changées).
    """
    assert analyse.video is not None
    retenus = au_dessus(candidats, config.min_score)
    choix = [(CORRIGER, t('ui.ligne_corriger')), (OPTIONS, t('ui.ligne_options', resume=resume_options(config)))]
    choix += [(str(i), ligne(c)) for i, c in enumerate(retenus[:nombre])]
    while True:
        reponse = ui.choisir(entete(analyse, candidats, retenus, config, nombre), choix)
        if reponse is None:
            return 1
        if reponse == CORRIGER:
            titre = (ui.saisir(t('ui.titre_corriger'), titre_lisible(analyse.video)) or '').strip()
            if titre:
                return Relance(titre=titre)
            continue  # saisie annulée : retour à la liste
        if reponse == OPTIONS:
            nouvelle = demander_options(config, ui)
            if nouvelle is not None:
                return Relance(config=nouvelle)
            continue
        candidat = retenus[int(reponse)]
        with ui.attente(t('ui.telechargement', source=candidat.source)):
            telecharge = telecharger(candidat, config)
        if not telecharge:
            ui.erreur(t('ui.echec_telechargement', source=candidat.source, chemin=analyse.chemin))
            continue
        try:
            resultat = enregistrer(candidat.sous_titre, analyse, config)
        except (OSError, ValueError) as e:
            ui.erreur(t('ui.erreur_ecriture', erreur=e))
            return 2
        if resultat.chemin is None:
            assert resultat.doublon_de is not None
            ui.informer(t('ui.doublon', nom=resultat.doublon_de.name))
            continue
        ui.notifier(t('ui.enregistre', nom=resultat.chemin.name))
        return 0


def choisir(chemin: Path, config: Config, ui: Interface, nombre: int | None = None) -> int:
    """Parcours complet pour une vidéo ; renvoie 0 (enregistré), 1 (annulé) ou 2 (erreur).

    La liste montre tous les candidats au-dessus de `min_score` (`nombre` : les N meilleurs seulement).
    """
    try:
        analyse = analyser(chemin, config)
    except (ValueError, OSError) as e:
        ui.erreur(t('ui.erreur_video', erreur=e))
        return 2
    if not dossier_inscriptible(chemin):
        ui.erreur(t('ui.dossier_protege', dossier=chemin.parent))
        return 2
    question = t('ui.titre_introuvable', nom=chemin.name)
    while True:
        # R1 : titre non reconnu → saisie, puis nouvelle analyse.
        if analyse.video is None:
            titre = (ui.saisir(question, chemin.stem) or '').strip()
            if not titre:
                return 1
            analyse = analyser(chemin, config, titre)
            question = t('ui.toujours_introuvable', titre=titre)
            continue
        video = analyse.video
        with ui.attente(t('ui.recherche', titre=titre_lisible(video))):
            affiner(video, config)
            candidats = lister(video, config)
        issue = proposer(analyse, candidats, config, ui, nombre)
        if isinstance(issue, int):
            return issue
        if issue.config is not None:
            config = issue.config
        if issue.titre is not None:
            analyse = analyser(chemin, config, issue.titre)
            question = t('ui.toujours_introuvable', titre=issue.titre)
