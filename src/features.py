"""
Préparation pour la modélisation : imputation + encodage + découpage train/test.

Pourquoi un Pipeline et pas des fichiers déjà imputés/encodés ?
Imputer (médiane...) ou encoder en regardant TOUTES les données fait "fuiter" des
informations du jeu de test vers l'entraînement. On apprend donc ces transformations
sur le train seul, puis on les applique telles quelles au test et à l'app Streamlit.
Les fichiers data/processed restent lisibles (valeurs réelles) ; ce module fournit la
transformation, sauvegardée avec joblib pour l'app.

Usage :
    from src.features import preparer
    jeu = preparer(df)                       # df = un data/processed concaténé
    jeu["X_train"], jeu["y_train_classe"], jeu["y_train_conso"] ...
    jeu["preprocesseur"]                     # à réutiliser dans l'app
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

from .preprocessing import COLONNES_ANALYSE, ORDRE_ISOLATION, ORDRE_PERIODE

CIBLE_CLASSE = "etiquette_dpe"
CIBLE_CONSO = "conso_5_usages_par_m2_ep"

NUMERIQUES = ["surface_habitable_logement", "hauteur_sous_plafond"]
# Plancher bas à part : il contient "non applicable", qui ne rentre pas dans l'échelle
COLS_ISOLATION = ["qualite_isolation_enveloppe", "qualite_isolation_murs",
                  "qualite_isolation_menuiseries"]
ORDINALES = ["periode_construction"] + COLS_ISOLATION
NOMINALES = ["type_batiment", "type_energie_principale_chauffage",
             "type_installation_chauffage", "type_installation_ecs",
             "qualite_isolation_plancher_bas", "origine"]

# Jamais dans X : cibles, colonnes contenant la réponse, identifiants, texte géographique, date
EXCLUES = [CIBLE_CLASSE, CIBLE_CONSO, *COLONNES_ANALYSE, "numero_dpe", "date_reception_dpe",
           "code_departement_ban", "code_postal_ban", "nom_commune_ban", "code_insee_ban"]
FEATURES = NUMERIQUES + ORDINALES + NOMINALES


def _en_objet(x):
    """dtype "string" de pandas (pd.NA) -> object (np.nan) : SimpleImputer ne gère pas pd.NA."""
    return pd.DataFrame(x).astype(object).where(pd.DataFrame(x).notna(), np.nan)


def _en_float(x):
    return pd.DataFrame(x).astype(float)


def construire_preprocesseur():
    """ColumnTransformer non appris. Valeurs inconnues (nouvelle période, nouvelle
    modalité) : codées -1 pour les ordinales, ignorées (zéros) pour les nominales."""
    num = Pipeline([("float", FunctionTransformer(_en_float, feature_names_out="one-to-one")), ("imp", SimpleImputer(strategy="median", add_indicator=True))])
    ordinal_pipe = Pipeline([
        ("objet", FunctionTransformer(_en_objet, feature_names_out="one-to-one")),
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("enc", OrdinalEncoder(
            categories=[ORDRE_PERIODE] + [ORDRE_ISOLATION] * len(COLS_ISOLATION),
            handle_unknown="use_encoded_value", unknown_value=-1)),
    ])
    nominal_pipe = Pipeline([
        ("objet", FunctionTransformer(_en_objet, feature_names_out="one-to-one")),
        ("imp", SimpleImputer(strategy="constant", fill_value="Inconnu")),
        ("enc", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([("num", num, NUMERIQUES),
                              ("ord", ordinal_pipe, ORDINALES),
                              ("nom", nominal_pipe, NOMINALES)])


def verifier_entree(df):
    manquantes = [c for c in FEATURES + [CIBLE_CLASSE, CIBLE_CONSO] if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes absentes du jeu nettoyé : {manquantes}")


def preparer(df, test_size=0.2, seed=42, chemin_sauvegarde=None):
    """Découpe en train/test (stratifié sur la classe DPE) puis apprend le
    préprocesseur sur le TRAIN seul. Renvoie un dict prêt pour la modélisation."""
    verifier_entree(df)
    df = df.reset_index(drop=True)
    X, y_classe, y_conso = df[FEATURES], df[CIBLE_CLASSE].astype(str), df[CIBLE_CONSO]
    (X_tr, X_te, yc_tr, yc_te, yr_tr, yr_te) = train_test_split(
        X, y_classe, y_conso, test_size=test_size, random_state=seed, stratify=y_classe)
    prep = construire_preprocesseur().fit(X_tr)  # apprentissage sur le train uniquement
    noms = list(prep.get_feature_names_out())

    def tr(x):
        return pd.DataFrame(prep.transform(x), columns=noms, index=x.index)

    jeu = {"X_train": tr(X_tr), "X_test": tr(X_te),
           "y_train_classe": yc_tr, "y_test_classe": yc_te,
           "y_train_conso": yr_tr, "y_test_conso": yr_te,
           "preprocesseur": prep, "colonnes": noms,
           "origine_test": df.loc[X_te.index, "origine"]}  # pour évaluer sur existants seuls
    if chemin_sauvegarde:
        joblib.dump(prep, chemin_sauvegarde)
    return jeu


def charger_preprocesseur(chemin):
    return joblib.load(chemin)


# ---------------------------------------------------------------------------
# Écriture / lecture du jeu prêt pour les modèles
# ---------------------------------------------------------------------------
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_PRET = RACINE / "data" / "ready"


def _ecrire(df, chemin, fmt):
    if fmt == "parquet":
        df.to_parquet(chemin.with_suffix(".parquet"), index=False)
    else:
        df.to_csv(chemin.with_suffix(".csv"), index=False)


def _lire(chemin, fmt):
    if fmt == "parquet":
        return pd.read_parquet(chemin.with_suffix(".parquet"))
    return pd.read_csv(chemin.with_suffix(".csv"))


def ecrire_jeu(jeu, dossier, snapshot, fmt="parquet"):
    """Écrit le jeu dans `dossier` : X et y (train/test), le préprocesseur, un meta.json.
    Les lignes de X_train et y_train_* sont alignées par leur ORDRE (même numéro de ligne)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    for nom in ["X_train", "X_test"]:
        _ecrire(jeu[nom].reset_index(drop=True), dossier / nom, fmt)
    for nom in ["y_train_classe", "y_test_classe", "y_train_conso", "y_test_conso", "origine_test"]:
        _ecrire(jeu[nom].reset_index(drop=True).to_frame(), dossier / nom, fmt)
    joblib.dump(jeu["preprocesseur"], dossier / "preprocesseur.joblib")
    meta = {"snapshot": snapshot, "cree_le": datetime.now().isoformat(timespec="seconds"),
            "format": fmt, "lignes_train": len(jeu["X_train"]), "lignes_test": len(jeu["X_test"]),
            "colonnes": jeu["colonnes"], "cibles": [CIBLE_CLASSE, CIBLE_CONSO]}
    (dossier / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def charger_jeu(snapshot=None, fmt="parquet", racine=DOSSIER_PRET):
    """Relit le jeu écrit par ecrire_jeu. Sans snapshot : le plus récent.
    Renvoie le même dictionnaire que preparer()."""
    racine = Path(racine)
    if snapshot is None:
        existants = sorted(d.name for d in racine.iterdir() if (d / "meta.json").exists())
        if not existants:
            raise FileNotFoundError(f"Aucun jeu dans {racine}. Lancer : python -m src.features")
        snapshot = existants[-1]
    dossier = racine / snapshot
    jeu = {}
    for nom in ["X_train", "X_test"]:
        jeu[nom] = _lire(dossier / nom, fmt)
    for nom in ["y_train_classe", "y_test_classe", "y_train_conso", "y_test_conso", "origine_test"]:
        jeu[nom] = _lire(dossier / nom, fmt).iloc[:, 0]
    jeu["preprocesseur"] = joblib.load(dossier / "preprocesseur.joblib")
    jeu["colonnes"] = json.loads((dossier / "meta.json").read_text(encoding="utf-8"))["colonnes"]
    return jeu


def main():
    from .data.repository import DataRepository
    p = argparse.ArgumentParser(description="Écrit le jeu train/test encodé dans data/ready/<snapshot>/.")
    p.add_argument("--snapshot", help="id du snapshot (défaut : le plus récent)")
    args = p.parse_args()
    repo = DataRepository()
    snap = args.snapshot or repo.latest_snapshot()
    df = pd.concat(repo.load_processed(snap).values(), ignore_index=True)
    jeu = preparer(df)
    ecrire_jeu(jeu, DOSSIER_PRET / snap, snap)
    print(f"Snapshot {snap} : {len(jeu['X_train'])} lignes d'entraînement, "
          f"{len(jeu['X_test'])} de test, {len(jeu['colonnes'])} colonnes.")
    print(f"Écrit dans : {DOSSIER_PRET / snap}")


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    # On passe par l'import du module : lancé avec `python -m src.features`, ce fichier
    from src.features import main as _main
    _main()