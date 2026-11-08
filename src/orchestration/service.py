from ..data.repository import DataRepository
from ..processing.analysis import StatAnalyzer
from ..models.registry import ModelRegistry
import numpy as np
import pandas as pd

class AppService():
    """Façade : seul point d'entrée du front vers les données, les statistiques et les modèles."""

    def __init__(self, repository:DataRepository|None=None, registry:ModelRegistry|None=None):
        self.__repository:DataRepository = repository if repository is not None else DataRepository()
        self.__analyzer:StatAnalyzer = StatAnalyzer()
        self.__registry:ModelRegistry = registry if registry is not None else ModelRegistry()
        self.__cache_modeles:dict = {}          # {(tache, departement): modèle}, chargé une seule fois
        self.__cache_evaluation:dict = {}       # {(tache, departement, nom): DataFrame}
        self.__snapshot_stats:str|None = None   # snapshot dont on affiche les statistiques
        self.__cache_stats:dict = {}            # {(snapshot, nom): DataFrame}, évite de relire le disque
        self.__cache_formulaire:dict|None = None   # résultat de formulaire(), lit les données une seule fois
        # snapshot des modèles, figé pour que modèles en cache et métadonnées restent cohérents (None : le plus récent)
        self.__snapshot_modeles:str|None = self.__repository.modeles_actifs()
        pass

    def snapshot_stats(self)-> str:
        """Id du snapshot actif, sinon du snapshot le plus récent qui a des statistiques calculées."""
        if self.__snapshot_stats is None:
            self.__snapshot_stats = self.__repository.snapshot_actif()
        if self.__snapshot_stats is None:
            snapshots = self.__repository.list_stats_snapshots()
            if not snapshots:
                raise FileNotFoundError("Aucune statistique calculée. Lancez : python -m src.orchestration.train --stats")
            self.__snapshot_stats = snapshots[-1]
        return self.__snapshot_stats

    def liste_stats(self)-> list[str]:
        """Noms des statistiques disponibles (ex. "kpi_globaux", "communes"...)."""
        return self.__repository.list_stats(self.snapshot_stats())

    def get_stat(self, nom:str)-> pd.DataFrame:
        """Renvoie une statistique pré-calculée (une copie : une page peut la filtrer
        ou la trier sans gêner les autres utilisateurs)."""
        snapid = self.snapshot_stats()
        cle = (snapid, nom)
        if cle not in self.__cache_stats:
            self.__cache_stats[cle] = self.__repository.load_stat(snapid, nom)
        return self.__cache_stats[cle].copy()

    def recharger_stats(self)-> None:
        """À appeler après un nouveau calcul (ex. après un rafraîchissement des données)."""
        self.__snapshot_stats = None
        self.__cache_stats.clear()

    def info_modele(self, tache:str, departement:str)-> dict:
        """meta.json du modèle le plus récent : colonnes attendues, métriques, k retenu...

        Raises:
            FileNotFoundError: pas de modèle pour ce département (le message liste ceux disponibles)
        """
        try:
            return self.__registry.load_meta(tache, departement, self.__snapshot_modeles)
        except FileNotFoundError:
            raise FileNotFoundError(f"Pas de modèle {tache} pour le département {departement}. "
                                    f"Départements disponibles : {self.__registry.list_departements(tache, self.__snapshot_modeles)}")

    def predire(self, tache:str, departement:str, X:pd.DataFrame)-> np.ndarray:
        """Prédit avec le modèle du département (ex. "75", déduit des 2 premiers chiffres du code postal).
        X doit contenir les colonnes données par info_modele(tache, departement)["colonnes"]."""
        cle = (tache, departement)
        if cle not in self.__cache_modeles:
            self.info_modele(tache, departement)   # erreur explicite si le modèle n'existe pas
            self.__cache_modeles[cle] = self.__registry.load(tache, departement, self.__snapshot_modeles)
        return self.__cache_modeles[cle].predict(X)

    def liste_evaluation(self, tache:str, departement:str)-> list[str]:
        """Noms des tableaux de performance du modèle (ex. "scores", "matrice_confusion"...)."""
        return self.info_modele(tache, departement).get("evaluation", [])

    def evaluation_modele(self, tache:str, departement:str, nom:str)-> pd.DataFrame:
        """Tableau de performance du modèle le plus récent, prêt à tracer ou à afficher
        (une copie, comme get_stat)."""
        cle = (tache, departement, nom)
        if cle not in self.__cache_evaluation:
            self.info_modele(tache, departement)   # erreur explicite si le modèle n'existe pas
            self.__cache_evaluation[cle] = self.__registry.load_evaluation(tache, departement, nom, self.__snapshot_modeles)
        return self.__cache_evaluation[cle].copy()


    def formulaire(self)-> dict:
        """Renvoie, pour chaque tâche et département, la cible et les champs du formulaire de prédiction
        (modèle le plus récent de chaque département, comme predire()).

        Forme du dictionnaire :
        {
            "snapshot": <id du snapshot le plus récent>,
            "classification": {
                <num_departement>: {
                    "cible": <nom de la cible>,
                    "champs": {<colonne>: <description du champ, cf. champs()>, ...}
                },
                ...
            },
            "regression": { même forme }
        }

        Raises:
            FileNotFoundError: aucun modèle entraîné
        """
        if self.__cache_formulaire is not None:
            return self.__cache_formulaire

        resultat = {"snapshot": None, "classification": {}, "regression": {}}
        donnees = {}   # {snapshot: {departement: DataFrame}}, chaque snapshot n'est lu qu'une fois
        for tache in ("classification", "regression"):
            for departement in self.__registry.list_departements(tache, self.__snapshot_modeles):
                meta = self.__registry.load_meta(tache, departement, self.__snapshot_modeles)
                snapid = meta.get("snapshot_source", meta["snapshot_id"])
                if snapid not in donnees:
                    donnees[snapid] = self.__repository.load_processed(snapid)
                resultat[tache][departement] = {
                    "cible": meta["cible"],
                    "champs": self.champs(donnees[snapid][departement], meta["colonnes"]),
                }

        if not donnees:
            raise FileNotFoundError("Aucun modèle entraîné. Lancez : python -m src.orchestration.train --train")
        resultat["snapshot"] = max(donnees)
        self.__cache_formulaire = resultat
        return resultat

    @staticmethod
    def champs(df:pd.DataFrame, colonnes:list[str])-> dict:
        """Décrit chaque colonne du formulaire à partir des données d'entraînement.

        Returns:
            {<colonne>: {"type": "nombre", "min": <min>, "max": <max>}}   pour une colonne numérique
            {<colonne>: {"type": "choix", "choix": <valeurs triées>}}   sinon
        """
        resultat = {}
        for colonne in colonnes:
            valeurs = df[colonne].dropna()
            if pd.api.types.is_numeric_dtype(valeurs):
                resultat[colonne] = {"type": "nombre", "min": float(valeurs.min()), "max": float(valeurs.max())}
            else:
                resultat[colonne] = {"type": "choix", "choix": sorted(valeurs.unique())}
        return resultat
