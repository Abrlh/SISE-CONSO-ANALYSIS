from typing import Any

import pandas as pd
import requests


class AdemeApiClient:
    TIMEOUT = 30  # secondes
    __API_URLS= {
        "dpe_existants": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines",
        "dpe_neufs": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe02neuf/lines"
    }

    __API_NAMES = list(__API_URLS.keys())



    def __init__(self):
        self._params: dict = {}


    def get_api_url(self, name: str) -> str:
        if name not in self.__API_URLS:
            raise ValueError(f"Nom d'API inconnu : {name}. Vérifiez le nom de l'API.")
        return self.__API_URLS[name]

    def get_all_api_urls(self) -> dict:
        return self.__API_URLS

    def get_full_datasets(self,code_departement:int,size:int=10000)-> dict:
        """Récupère l'ensemble des datasets disponibles pour un département donné.

        Args:
            code_departement: code du département
            size: nombre de lignes à récupérer par dataset (par défaut 10000)
        """
        datasets = {}
        for name in self.__API_NAMES:
            datasets[name] = self.get_dataset(name=name, code_departement=code_departement, size=size)
        return datasets

    def get_dataset(self, name: str,code_departement:int, **kwargs) -> pd.DataFrame:
        """Définit les paramètres puis interroge l'API `name` en un seul appel.

        Args:
            name: nom de l'API (ajoutée avec add_api_url)
            code_departement: code du département
            **kwargs: paramètres de la requête, fusionnés avec les valeurs par défaut de set_params
        """
        self.set_params(qs=code_departement,**kwargs)
        return self.request_api(name)

    def set_params(self, page: int = 1, size: int = 10000, select: str = None,
                   q: str = None, q_field: str = None, qs: str = None,
                   params: dict = None) -> None:
        """Définit les paramètres de la prochaine requête.

        Args:
            page: numéro de page
            size: nombre de lignes par page
            select: champs à récupérer
            q: recherche plein texte
            q_field: champ(s) sur lesquels porte q
            qs: requête filtrée (syntaxe query string)
            params: paramètres supplémentaires, prioritaires sur les arguments ci-dessus

        Les valeurs à None ne sont pas envoyées.
        """
        all_params = {"page": page, "size": size, "select": select,
                      "q": q, "q_fields": q_field, "qs": f"code_departement_ban:{qs}"}
        if params:
            all_params.update(params)
        self._params = {k: v for k, v in all_params.items() if v is not None}

    def request_api(self, name: str) -> pd.DataFrame:
        """Interroge l'API `name` avec les paramètres courants.

        Raises:
            ValueError: URL inconnue ou paramètres non définis
            requests.HTTPError: réponse HTTP en erreur
        """
        if name not in self.__API_URLS:
            raise ValueError(f"Nom d'API inconnu : {name}. Vérifiez le nom de l'API.")
        if not self._params:
            raise ValueError("Paramètres non définis. Utilisez set_params() pour les définir avant d'appeler request_api().")

        rep = requests.get(self.__API_URLS[name], params=self._params, timeout=self.TIMEOUT)
        rep.raise_for_status()
        return pd.DataFrame(rep.json()["results"])
