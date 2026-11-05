from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance


class BaseModel(ABC):
    def __init__(self):
        # hyperparamètres choisis pendant train() (ex. k de la sélection), notés dans meta.json
        self.meilleurs_params:dict = {}

    @abstractmethod
    def train(self, X:pd.DataFrame,Y:pd.Series)->None:
        """Entraîne le modèle.

        Args:
            X: variables d'entrée
            Y: cible
        """
        pass

    def predict(self, X:pd.DataFrame)-> np.ndarray:
        pass

    def evaluate(self, X:pd.DataFrame, Y:pd.Series)-> dict:
        pass

    def tableaux_evaluation(self, X:pd.DataFrame, y:pd.Series, y_train:pd.Series)-> dict[str, pd.DataFrame]:
        """Tableaux de performance pour le front, calculés sur le jeu de test (X, y).

        Args:
            y_train: sert à la référence naïve

        Returns:
            {nom_tableau: DataFrame}
        """
        pass

    def importance_variables(self, X:pd.DataFrame, y:pd.Series, scoring:str, n:int=5000)-> pd.DataFrame:
        """Importance par permutation, calculée sur un échantillon de n lignes.

        Returns:
            DataFrame variable, importance, ecart_type, la plus importante d'abord
        """
        echantillon = X.sample(min(n, len(X)), random_state=42)
        res = permutation_importance(self.model, echantillon, y.loc[echantillon.index], scoring=scoring,
                                     n_repeats=3, random_state=42, n_jobs=-1)
        return pd.DataFrame({"variable": X.columns, "importance": res.importances_mean,
                             "ecart_type": res.importances_std}
                            ).sort_values("importance", ascending=False, ignore_index=True)


def tableau_scores(reel:dict, reference:dict, libelles:dict)-> pd.DataFrame:
    """Une ligne par métrique : libellé, unité, valeur du modèle et valeur de la référence naïve.

    Args:
        reel: métriques du modèle sur le jeu de test
        reference: mêmes métriques pour la référence naïve
        libelles: {metrique: (libellé, unité)}, dans l'ordre d'affichage
    """
    return pd.DataFrame([{"metrique": m, "libelle": lib, "unite": unite,
                          "valeur": float(reel[m]), "reference_naive": float(reference[m])}
                         for m, (lib, unite) in libelles.items()])
