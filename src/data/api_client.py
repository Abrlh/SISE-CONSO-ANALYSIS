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

    def get_full_datasets(self,code_departement:int,size:int=10000,nb_page:int=5)-> dict:
        """Récupère l'ensemble des datasets disponibles pour un département donné.

        Args:
            code_departement: code du département
            size: taille de page pour la requête 
            nb_page: nombre maximum de pages à récupérer par dataset
        """
        datasets = {}
        for name in self.__API_NAMES:
            datasets[name] = self.get_dataset(name=name, code_departement=code_departement, nb_page=nb_page, size=size)
        return datasets

    def get_dataset(self, name: str,code_departement:int, nb_page:int=5, **kwargs) -> pd.DataFrame:
        """Définit les paramètres puis interroge l'API `name` en un seul appel.

        Args:
            name: nom de l'API (ajoutée avec add_api_url)
            code_departement: code du département
            nb_page: nombre maximum de pages à récupérer
            **kwargs: paramètres de la requête, fusionnés avec les valeurs par défaut de set_params
        """
        self.set_params(qs=code_departement,**kwargs)
        return self.request_api(name, nb_page)

    def set_params(self, page: int = 1, size: int = 10000, select: str = None,
                   q: str = None, q_field: str = None, qs: str = None,
                   params: dict = None) -> None:
        """Définit les paramètres de la prochaine requête.

        Args:
            page: numéro de page
            size: taille de la page
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

    def request_api(self, name: str,nb_page:int|None=5) -> pd.DataFrame:
        """Interroge l'API `name` avec les paramètres courants, sur au plus `nb_page` pages.
        Si `nb_page` est None, toutes les pages sont récupérées.

        Les pages suivantes sont récupérées via le lien `next` de la réponse
        (pagination par curseur), car l'API refuse page * size > 10000.

        Raises:
            ValueError: URL inconnue ou paramètres non définis
            requests.HTTPError: réponse HTTP en erreur
        """
        if name not in self.__API_URLS:
            raise ValueError(f"Nom d'API inconnu : {name}. Vérifiez le nom de l'API.")
        if not self._params:
            raise ValueError("Paramètres non définis. Utilisez set_params() pour les définir avant d'appeler request_api().")
        url, params = self.__API_URLS[name], self._params
        frames = []
        i = 0
        while url and (nb_page is None or i < nb_page):
            i += 1
            print(f"Récupération de la page {i}/{nb_page or '?'} pour l'API {name}...")
            rep = requests.get(url, params=params, timeout=self.TIMEOUT)
            rep.raise_for_status()
            data = rep.json()
            frames.append(pd.DataFrame(data["results"]))
            url, params = data.get("next"), None  # `next` contient déjà tous les paramètres
        return pd.concat(frames, ignore_index=True)