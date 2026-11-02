from .base import BaseModel, tableau_scores
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

class ClassificationModel(BaseModel):

    GRILLE_K = [20, 50, "all"]


    """Prédit l'étiquette DPE (A à G), même pipeline que le notebook 03_ML."""
    def __init__(self):
        super().__init__()
        preprocess = ColumnTransformer([

            ("quanti", Pipeline(
                [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())
                 ]),
             make_column_selector(dtype_include="number")),
            ("quali", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore"))
                ]),
             make_column_selector(dtype_exclude="number")),
        ], sparse_threshold=0)  # attention: HistGradientBoosting n'accepte pas la matrice creuse du OneHotEncoder
        self.model = Pipeline([
            ("preprocess", preprocess),
            ("variance", VarianceThreshold()),
            ("selection", SelectKBest()), 
            ("model", HistGradientBoostingClassifier(max_leaf_nodes=63, random_state=42)),
        ])


    def train(self, X, y):
        search = GridSearchCV(self.model, {"selection__k": self.GRILLE_K}, cv=2, scoring="f1_macro")
        search.fit(X, y)
        self.model = search.best_estimator_
        self.meilleurs_params = search.best_params_

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
    return {
        "f1_macro": f1_score(y, y_pred, average="macro"),
        "accuracy": accuracy_score(y, y_pred),
        "a_une_classe_pres": (ecart <= 1).mean(),
        "rapport": classification_report(y, y_pred, output_dict=True),
    }
