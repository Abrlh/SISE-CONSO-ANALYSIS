from .base import BaseModel, tableau_scores
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

class RegressionModel(BaseModel):
    """Prédit la consommation (kWh/m²/an), même pipeline que le notebook 03_ML (gradient boosting réglé).

    Pas de sélection de variables : SelectKBest n'accepte pas les cases vides, que ce pipeline
    laisse passer jusqu'au modèle (le gradient boosting les gère lui-même).
    """
    def __init__(self):
        super().__init__()
        preprocess = ColumnTransformer([
            ("quanti", "passthrough", make_column_selector(dtype_include="number")),
            ("quali", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan,
                                     encoded_missing_value=np.nan),
             make_column_selector(dtype_exclude="number")),
        ])
        self.model = Pipeline([
            ("preprocess", preprocess),
            # réglages retenus par la grille du notebook
            ("model", HistGradientBoostingRegressor(learning_rate=0.1, max_leaf_nodes=31, min_samples_leaf=50,
                                                    max_iter=1000, early_stopping=True,
                                                    n_iter_no_change=20, random_state=42)),
        ])

    def train(self, X, y):
        self.model.fit(X, y)

    def predict(self, X)-> np.ndarray:
        return self.model.predict(X)

    def evaluate(self, X, y)-> dict:
        return metriques(y, self.predict(X))

    # {metrique: (libellé, unité)} du tableau "scores"
    LIBELLES = {"r2": ("Part de la variation de consommation expliquée (1 = parfait)", ""),
                "mae": ("Erreur moyenne", "kWh/m²/an"),
                "rmse": ("Erreur quadratique moyenne (pèse plus les grosses erreurs)", "kWh/m²/an")}
    # tranches de consommation réelle du tableau "erreur_par_tranche" (kWh/m²/an)
    BORNES_TRANCHES = [0, 50, 100, 150, 200, 300, 400]
    TAILLE_ECHANTILLON = 2000   # points du nuage "prédit contre réel"

    def tableaux_evaluation(self, X, y, y_train)-> dict[str, pd.DataFrame]:
        y_pred = self.predict(X)
        reel = np.asarray(y, dtype=float)
        erreur = y_pred - reel                       # > 0 : le modèle surestime
        # référence naïve : prédire toujours la médiane de l'entraînement
        naif = np.full(len(y), float(np.median(y_train)))

        nuage = (pd.DataFrame({"reel": reel, "predit": y_pred})
                 .sample(min(self.TAILLE_ECHANTILLON, len(reel)), random_state=42).reset_index(drop=True))

        lignes = []
        bornes = self.BORNES_TRANCHES + [None]       # None : dernière tranche ouverte
        for bmin, bmax in zip(bornes[:-1], bornes[1:]):
            dans = (reel >= bmin) & ((reel < bmax) if bmax is not None else True)
            e = erreur[dans]
            lignes.append({"tranche": f"{bmin}-{bmax}" if bmax is not None else f"{bmin} et plus",
                           "borne_min": bmin, "borne_max": bmax, "effectif": int(dans.sum()),
                           "erreur_absolue_moyenne": float(np.abs(e).mean()) if len(e) else np.nan,
                           "erreur_moyenne": float(e.mean()) if len(e) else np.nan})
        return {
            "scores": tableau_scores(metriques(y, y_pred), metriques(y, naif), self.LIBELLES),
            "predit_reel": nuage,
            "erreur_par_tranche": pd.DataFrame(lignes),
            "importance_variables": self.importance_variables(X, y, scoring="r2"),
        }


def metriques(y, y_pred)-> dict:
    """Scores de régression à partir des valeurs vraies et prédites."""
    return {
        "r2": r2_score(y, y_pred),
        "mae": mean_absolute_error(y, y_pred),     # kWh/m²/an
        "rmse": root_mean_squared_error(y, y_pred),
    }
