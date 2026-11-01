"""
Audit des colonnes d'un snapshot : repère les colonnes NOUVELLES (absentes de
docs/colonnes_retenues.csv) et les colonnes DISPARUES, et décrit les nouvelles.

Le nettoyage garde toutes les colonnes, sauf celles trop vides : une colonne nouvelle
entre donc automatiquement dans les données propres. Cet audit sert à voir ce qui est
apparu ou disparu, quelles nouvelles colonnes seront retirées (trop vides), et lesquelles
semblent contenir la réponse (à ne pas utiliser en entrée d'un modèle).

Lancé comme étape "audit" du pipeline (src/train.py) :
    python -m src.train --audit                       # dernier snapshot
    python -m src.train --audit --snapshot 2026-10-18_101500
Sortie : affichage + docs/audit_<snapshot>.csv
"""
from pathlib import Path

import pandas as pd

from .preprocessing import SEUIL_MANQUANT

RACINE = Path(__file__).resolve().parent.parent

# Seuils de l'audit (critères calculés, pas de liste codée en dur).
# SEUIL_MANQUANT est celui du nettoyage (src/preprocessing.py).
SEUIL_CORRELATION = 0.9   # quasi-identique à la consommation : fuite probable

# Familles de colonnes qui contiennent (ou reflètent) la réponse : fuite probable
PREFIXES_FUITE = ("conso_", "cout_", "emission_ges", "etiquette_", "deperditions",
                  "besoin", "ubat", "apport_", "production_", "indicateur_")
CIBLE = "conso_5_usages_par_m2_ep"
CSV_REFERENCE = RACINE / "docs" / "colonnes_retenues.csv"


def colonnes_connues(chemin=CSV_REFERENCE):
    """Les colonnes déjà vues (1re colonne du CSV de référence)."""
    ref = pd.read_csv(chemin)
    nom = "colonne" if "colonne" in ref.columns else ref.columns[0]
    return set(ref[nom].astype(str))


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

    if nom.startswith(PREFIXES_FUITE):
        ligne["suggestion"] = "ATTENTION : famille qui contient la réponse (pas en entrée d'un modèle)"
    elif corr is not None and abs(corr) >= SEUIL_CORRELATION:
        ligne["suggestion"] = "ATTENTION : quasi identique à la cible (fuite probable)"
    elif vides > SEUIL_MANQUANT:
        ligne["suggestion"] = f"Sera retirée par le nettoyage (vide à plus de {int(SEUIL_MANQUANT*100)} %)"
    else:
        ligne["suggestion"] = "Entrera dans les données propres"
    return ligne


def auditer(df, chemin_reference=CSV_REFERENCE):
    """Renvoie (nouvelles : DataFrame, disparues : liste)."""
    connues = colonnes_connues(chemin_reference)
    actuelles = set(df.columns)
    nouvelles = sorted(actuelles - connues - {"origine"})
    ref = pd.read_csv(chemin_reference)
    vues_gardees = set(ref[ref.columns[0]].astype(str)[ref["decision"] == "gardée"]) \
        if "decision" in ref.columns else connues
    disparues = sorted(c for c in vues_gardees - {"origine"} if c not in actuelles)
    cible = df[CIBLE] if CIBLE in df.columns else None
    desc = pd.DataFrame([decrire(df[c], cible) for c in nouvelles])
    if len(desc):
        # les candidates d'abord
        desc = desc.sort_values("suggestion", key=lambda x: ~x.str.startswith("ATTENTION"), kind="stable")
    return desc, disparues


def afficher(snap, tout, desc, disparues, sortie=None):
    """Affiche le résultat de auditer() ; sortie : chemin du CSV écrit (None si rien écrit)."""
    print(f"Snapshot {snap} : {len(tout)} lignes, {tout.shape[1]} colonnes")
    print(f"\nColonnes DISPARUES (déjà vues et gardées) : {disparues or 'aucune'}")
    print(f"\nColonnes NOUVELLES : {len(desc)}")
    if len(desc):
        with pd.option_context("display.max_colwidth", 70, "display.width", 200):
            print(desc.to_string(index=False))
        print(f"\nÉcrit : {sortie}")
        print("Les colonnes nouvelles non trop vides entrent automatiquement dans les données "
              "propres. Les noter dans docs/colonnes_retenues.csv pour qu'elles ne soient plus signalées.")
