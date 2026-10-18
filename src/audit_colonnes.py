"""
Audit des colonnes d'un snapshot : repère les colonnes NOUVELLES (absentes de
docs/colonnes_retenues.csv) et les colonnes DISPARUES, et décrit les nouvelles.

Le nettoyage ignore les colonnes nouvelles (liste blanche) : cet audit sert à décider,
à la main, si l'une d'elles mérite d'être ajoutée.

Usage :
    python -m src.audit_colonnes                      # dernier snapshot
    python -m src.audit_colonnes --snapshot 2026-10-18_101500
Sortie : affichage + docs/audit_<snapshot>.csv
"""
import argparse
from pathlib import Path

import pandas as pd

from .preprocessing import COLONNES_GARDEES

RACINE = Path(__file__).resolve().parent.parent

# Seuils de l'audit (critères calculés, pas de liste codée en dur)
SEUIL_MANQUANT = 0.6      # plus de 60 % de vide : écartée
SEUIL_MODALITES = 50      # plus de 50 valeurs différentes en texte : écartée
SEUIL_CORRELATION = 0.9   # quasi-identique à la consommation : fuite probable

# Familles de colonnes qui contiennent (ou reflètent) la réponse : fuite probable
PREFIXES_FUITE = ("conso_", "cout_", "emission_ges", "etiquette_", "deperditions",
                  "besoin", "ubat", "apport_", "production_", "indicateur_")
# Identifiants, adresses, texte libre : inutiles pour prédire
MOTS_IDENTIFIANT = ("numero_", "identifiant", "adresse", "nom_", "complement_",
                    "_brut", "_id", "id_", "description_", "date_")
CIBLE = "conso_5_usages_par_m2_ep"
CSV_REFERENCE = RACINE / "docs" / "colonnes_retenues.csv"


def colonnes_connues(chemin=CSV_REFERENCE):
    """Les 224 colonnes déjà examinées (1re colonne du CSV de décisions)."""
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
        ligne["suggestion"] = "ÉCARTER : famille qui contient la réponse (fuite)"
    elif corr is not None and abs(corr) >= SEUIL_CORRELATION:
        ligne["suggestion"] = "ÉCARTER : quasi identique à la cible (fuite probable)"
    elif any(m in nom for m in MOTS_IDENTIFIANT):
        ligne["suggestion"] = "ÉCARTER : identifiant, adresse, date ou texte libre"
    elif vides > SEUIL_MANQUANT:
        ligne["suggestion"] = f"ÉCARTER : trop vide (> {int(SEUIL_MANQUANT*100)} %)"
    elif nuniq <= 1:
        ligne["suggestion"] = "ÉCARTER : constante"
    elif not est_num and nuniq > SEUIL_MODALITES:
        ligne["suggestion"] = "ÉCARTER ou regrouper : trop de modalités"
    else:
        ligne["suggestion"] = "CANDIDATE : à examiner (utile ? saisissable dans l'app ?)"
    return ligne


def auditer(df, chemin_reference=CSV_REFERENCE):
    """Renvoie (nouvelles : DataFrame, disparues : liste)."""
    connues = colonnes_connues(chemin_reference)
    actuelles = set(df.columns)
    nouvelles = sorted(actuelles - connues - {"origine"})
    disparues = sorted(c for c in COLONNES_GARDEES if c not in actuelles and c != "origine")
    cible = df[CIBLE] if CIBLE in df.columns else None
    desc = pd.DataFrame([decrire(df[c], cible) for c in nouvelles])
    if len(desc):
        # les candidates d'abord
        desc = desc.sort_values("suggestion", key=lambda x: ~x.str.startswith("CANDIDATE"), kind="stable")
    return desc, disparues


def main():
    from .data.repository import DataRepository
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", help="id du snapshot (défaut : le plus récent)")
    args = p.parse_args()
    repo = DataRepository()
    snap = args.snapshot or repo.latest_snapshot()
    donnees = repo.load(snap)
    tout = pd.concat([d for dep in donnees.values() for d in dep.values()], ignore_index=True)
    desc, disparues = auditer(tout)
    print(f"Snapshot {snap} : {len(tout)} lignes, {tout.shape[1]} colonnes")
    print(f"\nColonnes DISPARUES parmi celles utilisées : {disparues or 'aucune'}")
    print(f"\nColonnes NOUVELLES : {len(desc)}")
    if len(desc):
        with pd.option_context("display.max_colwidth", 70, "display.width", 200):
            print(desc.to_string(index=False))
        sortie = RACINE / "docs" / f"audit_{snap}.csv"
        desc.to_csv(sortie, index=False)
        print(f"\nÉcrit : {sortie}")
        print("Pour en garder une : l'ajouter à COLONNES_GARDEES (+ type dans features.py), "
              "puis la noter dans docs/colonnes_retenues.csv.")


if __name__ == "__main__":
    main()
