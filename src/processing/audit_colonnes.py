"""
Audit des colonnes d'un snapshot brut :
1. colonnes utilisées par le code (nettoyage, modèles, statistiques) absentes ;
2. colonnes nouvelles ou disparues depuis le snapshot précédent.

Lancement : python -m src.orchestration.train --audit [--snapshot <id>]
Sortie : affichage + docs/audit_<snapshot>.csv (si colonnes nouvelles).
"""
import pandas as pd

from .analysis import COLONNES_UTILES
from .preprocessing import COLONNES_CREEES, COLONNES_OBLIGATOIRES, SEUIL_MANQUANT
from ..models.features import CIBLE_CLASSIFICATION, CIBLE_REGRESSION, PREFIXES_FUITE, PREFIXES_CALCUL, VARIABLES_FORMULAIRE

# Seuils de l'audit (critères calculés, pas de liste codée en dur).
# SEUIL_MANQUANT est celui du nettoyage (src/processing/preprocessing.py).
SEUIL_CORRELATION = 0.9   # quasi-identique à la consommation : fuite probable

# Familles de colonnes qui contiennent (ou reflètent) la réponse : PREFIXES_FUITE et PREFIXES_CALCUL,
# définis dans src/models/features.py (les mêmes listes servent à retirer ces colonnes des modèles)
# corrélation calculée avec la cible de la régression (même constante que l'entraînement)
CIBLE = CIBLE_REGRESSION

# colonnes utilisées par le code, et où : {usage: colonnes}
UTILISATIONS = {"nettoyage": COLONNES_OBLIGATOIRES,
                "formulaire": VARIABLES_FORMULAIRE,
                "cible": [CIBLE_CLASSIFICATION, CIBLE_REGRESSION],
                "statistiques": COLONNES_UTILES}


def colonnes_utilisees():
    """{colonne brute: [usages]} ; une colonne créée par le nettoyage est remplacée par sa source brute."""
    usages = {}
    for usage, colonnes in UTILISATIONS.items():
        for c in colonnes:
            c = COLONNES_CREEES.get(c, c)
            if c is not None:
                usages.setdefault(c, [])
                if usage not in usages[c]:
                    usages[c].append(usage)
    return usages


def decrire(serie, cible=None):
    """Une ligne de description + une suggestion (indicative, la décision reste humaine)."""
    n = len(serie)
    vides = serie.isna().mean() if n else 1.0
    nuniq = serie.nunique(dropna=True)
    num = pd.to_numeric(serie, errors="coerce")
    est_num = num.notna().sum() > 0.9 * serie.notna().sum() and serie.notna().sum() > 0
    nom = str(serie.name)
    ligne = {"colonne": nom, "type": "numérique" if est_num else "texte/catégorie",
             "pct_manquant": round(100 * vides, 1), "valeurs_distinctes": nuniq}
    if est_num:
        ligne["exemple"] = f"min={num.min():.3g} médiane={num.median():.3g} max={num.max():.3g}"
    else:
        top = serie.dropna().astype(str).value_counts().head(3)
        ligne["exemple"] = "; ".join(f"{k} ({v})" for k, v in top.items())

    corr = None
    if est_num and cible is not None and num.notna().sum() > 10 and nuniq > 1:
        corr = num.corr(pd.to_numeric(cible, errors="coerce"))
    ligne["corr_cible"] = None if corr is None or pd.isna(corr) else round(float(corr), 2)

    if nom.startswith(PREFIXES_FUITE + PREFIXES_CALCUL):
        ligne["suggestion"] = "ATTENTION : famille qui contient la réponse (pas en entrée d'un modèle)"
    elif corr is not None and abs(corr) >= SEUIL_CORRELATION:
        ligne["suggestion"] = "ATTENTION : quasi identique à la cible (fuite probable)"
    elif vides > SEUIL_MANQUANT:
        ligne["suggestion"] = f"Sera retirée par le nettoyage (vide à plus de {int(SEUIL_MANQUANT*100)} %)"
    else:
        ligne["suggestion"] = "Entrera dans les données propres"
    return ligne


def auditer(df, colonnes_precedentes=None):
    """Audite les colonnes de df (données brutes).

    Args:
        df: toutes les données brutes du snapshot
        colonnes_precedentes: colonnes du snapshot précédent, None s'il n'y en a pas

    Returns:
        (manquantes : {colonne: [usages]}, nouvelles : DataFrame, disparues : liste)
        nouvelles et disparues sont vides sans snapshot précédent.
    """
    actuelles = set(df.columns)
    manquantes = {c: u for c, u in colonnes_utilisees().items() if c not in actuelles}
    if colonnes_precedentes is None:
        return manquantes, pd.DataFrame(), []
    nouvelles = sorted(actuelles - set(colonnes_precedentes))
    disparues = sorted(set(colonnes_precedentes) - actuelles)
    cible = df[CIBLE] if CIBLE in df.columns else None
    desc = pd.DataFrame([decrire(df[c], cible) for c in nouvelles])
    if len(desc):
        # les candidates d'abord
        desc = desc.sort_values("suggestion", key=lambda x: ~x.str.startswith("ATTENTION"), kind="stable")
    return manquantes, desc, disparues


def afficher(snap, tout, manquantes, desc, disparues, snap_precedent=None, sortie=None):
    """Affiche le résultat de auditer() ; sortie : chemin du CSV écrit (None si rien écrit)."""
    print(f"Snapshot {snap} : {len(tout)} lignes, {tout.shape[1]} colonnes")
    if manquantes:
        print("\nATTENTION, colonnes UTILISÉES PAR LE CODE absentes :")
        for c, usages in manquantes.items():
            print(f"  {c} ({', '.join(usages)})")
    else:
        print("\nColonnes utilisées par le code : toutes présentes")
    if snap_precedent is None:
        print("\nPas de snapshot précédent : comparaison des colonnes sautée")
        return
    print(f"\nPar rapport au snapshot précédent ({snap_precedent}) :")
    print(f"  disparues : {disparues or 'aucune'}")
    print(f"  nouvelles : {len(desc)}")
    if len(desc):
        with pd.option_context("display.max_colwidth", 70, "display.width", 200):
            print(desc.to_string(index=False))
        print(f"\nÉcrit : {sortie}")
        print("Les colonnes nouvelles non trop vides entrent automatiquement dans les données propres.")
