from .data.repository import DataRepository
from .analysis import StatAnalyzer
from .models.registry import ModelRegistry
import pandas as pd

class AppService():
    """
    Starting point for the application service.
    Responsible for orchestrating the application logic,
    including data loading, preprocessing, statistical analysis, model info
    """

    def __init__(self, repository:DataRepository|None=None):
        self.__repository:DataRepository = repository if repository is not None else DataRepository()
        self.__analyzer:StatAnalyzer = StatAnalyzer()
        self.__registry:ModelRegistry = None
        self.__snapshot_stats:str|None = None   # snapshot dont on affiche les statistiques
        self.__cache_stats:dict = {}            # {(snapshot, nom): DataFrame}, évite de relire le disque
        pass

    def snapshot_stats(self)-> str:
        """Id du snapshot le plus récent qui a des statistiques calculées."""
        if self.__snapshot_stats is None:
            snapshots = self.__repository.list_stats_snapshots()
            if not snapshots:
                raise FileNotFoundError("Aucune statistique calculée. Lancez : python -m src.train --stats")
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

    