

from typing import Any

import pandas as pd


class DataPreprocessor():
    """ 
    Preprocesses the data for analysis and modeling.
    """

    def __init__(self):
        pass

    def process(self, datasets:dict)-> Any:
        """
        Args:
            datasets: {departement: {nom_dataset: DataFrame}}

        Returns:
            {departement: DataFrame}

        Version provisoire : fusionne seulement les datasets de chaque département,
        avec une colonne "origine" contenant le nom du dataset (ex. "dpe_existants").
        Aucun autre traitement.
        """
        # TODO: vrai prétraitement
        return {
            departement: pd.concat([df.assign(origine=name) for name, df in dfs.items()], ignore_index=True)
            for departement, dfs in datasets.items()
        }
