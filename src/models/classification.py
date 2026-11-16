from .base import BaseModel, tableau_scores
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

class ClassificationModel(BaseModel):
    """Prédit l'étiquette DPE (A à G) par gradient boosting.

    Même prétraitement que la régression : un entier par modalité, valeurs manquantes laissées au modèle.
    """
    def __init__(self):
        super().__init__()
        preprocess = ColumnTransformer([
            # qualitatives en premier : train() indique leurs positions au modèle
            # max_categories : le gradient boosting refuse plus de 255 modalités par variable
            ("quali", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan,
                                     encoded_missing_value=np.nan, max_categories=255),
             make_column_selector(dtype_exclude="number")),
            ("quanti", "passthrough", make_column_selector(dtype_include="number")),
        ])
        self.model = Pipeline([
            ("preprocess", preprocess),
            ("model", HistGradientBoostingClassifier(max_leaf_nodes=63, max_iter=1000, early_stopping=True,
                                                     random_state=42)),
        ])


    def train(self, X, y):
        nb_quali = X.select_dtypes(exclude="number").shape[1]
        self.model.set_params(model__categorical_features=list(range(nb_quali)))
        self.model.fit(X, y)

    def predict(self, X)-> np.ndarray:
        return self.model.predict(X)

    def evaluate(self, X, y)-> dict:
        return metriques(y, self.predict(X))

    # {metrique: (libellé, unité)} du tableau "scores"
    LIBELLES = {"f1_macro": ("Score F1 moyen sur les étiquettes (de 0 à 1)", ""),
                "accuracy": ("Part d'étiquettes exactes", ""),
                "a_une_classe_pres": ("Part d'étiquettes exactes ou à une classe près", "")}

    def tableaux_evaluation(self, X, y, y_train)-> dict[str, pd.DataFrame]:
        y_pred = self.predict(X)
        etiquettes = sorted(set(y) | set(y_pred))
        # référence naïve : prédire toujours l'étiquette la plus fréquente de l'entraînement
        naif = np.full(len(y), pd.Series(y_train).mode()[0])

        # matrice de confusion, format long ; pourcentage par vraie étiquette (ligne)
        matrice = (pd.DataFrame(confusion_matrix(y, y_pred, labels=etiquettes), index=etiquettes, columns=etiquettes)
                   .rename_axis(index="vraie", columns="predite").stack().rename("effectif").reset_index())
        total = matrice.groupby("vraie")["effectif"].transform("sum")
        matrice["pourcentage"] = (100 * matrice["effectif"] / total.where(total > 0)).round(2)

        rapport = classification_report(y, y_pred, labels=etiquettes, output_dict=True, zero_division=0)
        par_etiquette = pd.DataFrame([{"etiquette": e, "precision": rapport[e]["precision"],
                                       "rappel": rapport[e]["recall"], "f1": rapport[e]["f1-score"],
                                       "effectif": int(rapport[e]["support"])} for e in etiquettes])
        return {
            "scores": tableau_scores(metriques(y, y_pred), metriques(y, naif), self.LIBELLES),
            "matrice_confusion": matrice,
            "par_etiquette": par_etiquette,
            "importance_variables": self.importance_variables(X, y, scoring="f1_macro"),
        }


def metriques(y, y_pred)-> dict:
    """Scores de classification à partir des étiquettes vraies et prédites."""
    # écart en nombre de classes entre la vraie étiquette et la prédiction (A et C -> 2)
    ecart = np.abs(pd.Series(y).map(ord).to_numpy() - pd.Series(y_pred).map(ord).to_numpy())
    # zero_division=0 : une étiquette jamais prédite (cas normal de la référence naïve) a une précision de 0,
    # sans avertissement ; pour le vrai modèle, le tableau par_etiquette le montre (précision à 0)
    return {
        "f1_macro": f1_score(y, y_pred, average="macro", zero_division=0),
        "accuracy": accuracy_score(y, y_pred),
        "a_une_classe_pres": (ecart <= 1).mean(),
        "rapport": classification_report(y, y_pred, output_dict=True, zero_division=0),
    }
