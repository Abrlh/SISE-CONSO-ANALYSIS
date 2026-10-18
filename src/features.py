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
