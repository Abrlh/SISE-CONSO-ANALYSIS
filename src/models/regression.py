from .base import BaseModel
import numpy as np
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
        y_pred = self.predict(X)
        return {
            "r2": r2_score(y, y_pred),
            "mae": mean_absolute_error(y, y_pred),     # kWh/m²/an
            "rmse": root_mean_squared_error(y, y_pred),
        }
