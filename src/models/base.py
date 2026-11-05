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
        """ Train the model with the provided features and target values.
        Args:
            X (pd.DataFrame): The input features for training.
            Y (pd.Series): The target values for training.
        """
        pass

    def predict(self, X:pd.DataFrame)-> np.ndarray:
        pass

    def evaluate(self, X:pd.DataFrame, Y:pd.Series)-> dict:
        pass

    def tableaux_evaluation(self, X:pd.DataFrame, y:pd.Series, y_train:pd.Series)-> dict[str, pd.DataFrame]:
        """Données de performance pour le front (des tableaux à tracer, pas des images),
        calculées sur le jeu de test (X, y). y_train sert à la référence naïve.

        Returns:
            {nom_tableau: DataFrame}, enregistrés avec le modèle par ModelRegistry
        """
        pass

    def importance_variables(self, X:pd.DataFrame, y:pd.Series, scoring:str, n:int=5000)-> pd.DataFrame:
        """Importance par permutation (comme dans le notebook) : on mélange une variable et on mesure
        de combien le score baisse. Calculée sur un échantillon de n lignes pour rester rapide.

        Returns:
            colonnes variable, importance (baisse moyenne du score), ecart_type ; la plus importante d'abord
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
