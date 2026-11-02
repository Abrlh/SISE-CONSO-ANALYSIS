from .base import BaseModel
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, f1_score
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
        self.meilleurs_params:dict = {}


    def train(self, X, y):
        search = GridSearchCV(self.model, {"selection__k": self.GRILLE_K}, cv=2, scoring="f1_macro")
        search.fit(X, y)
        self.model = search.best_estimator_
        self.meilleurs_params = search.best_params_

    def predict(self, X)-> np.ndarray:
        return self.model.predict(X)

    def evaluate(self, X, y)-> dict:
        y_pred = self.predict(X)
        # écart en nombre de classes entre la vraie étiquette et la prédiction (A et C -> 2)
        ecart = np.abs(pd.Series(y).map(ord).to_numpy() - pd.Series(y_pred).map(ord).to_numpy())
        return {
            "f1_macro": f1_score(y, y_pred, average="macro"),
            "accuracy": accuracy_score(y, y_pred),
            "a_une_classe_pres": (ecart <= 1).mean(),
            "rapport": classification_report(y, y_pred, output_dict=True),
        }
