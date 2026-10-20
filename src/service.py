from datetime import datetime

import pandas as pd

from .config import PROJECT_ROOT
from .data.repository import DataRepository
from .analysis import StatAnalyzer
from .models.registry import ModelRegistry

# Données prétraitées : data/processed/<snapshot_id>/<departement>.parquet + meta.json
DOSSIER_PROCESSED = PROJECT_ROOT / "data" / "processed"


class AppService():
    """
    Starting point for the application service.
    Responsible for orchestrating the application logic,
    including data loading, preprocessing, statistical analysis, model info

    Règles (voir app/deps.py) : cet objet est créé une seule fois et partagé entre tous les utilisateurs.
    Il ne contient donc aucune donnée propre à un utilisateur, et les DataFrame qu'il renvoie
    ne doivent jamais être modifiés par les pages (faire df.copy() avant de modifier).
    """

    def __init__(self):
        self.__repository:DataRepository = DataRepository()
        self.__analyzer:StatAnalyzer = StatAnalyzer()
        self.__registry:ModelRegistry = ModelRegistry()
        self.__cache:dict = {}  # {snapshot_id: DataFrame}, évite de relire les fichiers à chaque interaction

    # ------------------------------------------------------------------ snapshots

    def list_snapshots(self) -> list[str]:
        """Ids des snapshots prétraités complets (dossiers contenant meta.json), du plus ancien au plus récent."""
        if not DOSSIER_PROCESSED.exists():
            return []
        return sorted(p.name for p in DOSSIER_PROCESSED.iterdir() if (p / "meta.json").exists())

    def latest_snapshot(self) -> str:
        """Id du snapshot prétraité le plus récent. Lève FileNotFoundError s'il n'y en a aucun."""
        snapshots = self.list_snapshots()
        if not snapshots:
            raise FileNotFoundError(
                "Aucune donnée prétraitée dans data/processed/. "
                "Lancez : python -m src.train --preprocess (voir docs/nettoyage_donnees.md)."
            )
        return snapshots[-1]

    # ------------------------------------------------------------------ données

    def load_data(self, snapshot_id:str|None=None) -> pd.DataFrame:
        """Tous les départements d'un snapshot prétraité dans un seul tableau (le plus récent par défaut).

        Le tableau est gardé en mémoire : il ne doit pas être modifié, travailler sur une copie.
        """
        if snapshot_id is None:
            snapshot_id = self.latest_snapshot()
        if snapshot_id not in self.__cache:
            par_departement = self.__repository.load_processed(snapshot_id)
            df = pd.concat(par_departement.values(), ignore_index=True)
            # Un seul snapshot en mémoire à la fois (mémoire limitée sur l'hébergement)
            self.__cache = {snapshot_id: self.__alleger(df)}
        return self.__cache[snapshot_id]

    def __alleger(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convertit les colonnes de texte peu variées en catégories pour réduire la mémoire utilisée."""
        for colonne in df.columns:
            if pd.api.types.is_string_dtype(df[colonne]) and df[colonne].nunique() < 1000:
                df[colonne] = df[colonne].astype("category")
        return df

    def get_apercu(self, n:int=20, snapshot_id:str|None=None) -> pd.DataFrame:
        """Les n premières lignes du tableau (une copie), pour un aperçu."""
        return self.load_data(snapshot_id).head(n).copy()

    def __date_snapshot(self, snapshot_id:str) -> str:
        """Date lisible d'un id de snapshot, ex. '2026-10-12_132605' -> '12/10/2026'."""
        try:
            return datetime.strptime(snapshot_id, DataRepository.SNAPSHOT_ID_FORMAT).strftime("%d/%m/%Y")
        except ValueError:
            return snapshot_id

    # ------------------------------------------------------------------ statistiques

    def get_stats(self, snapshot_id:str|None=None) -> dict:
        """Statistiques nécessaires aux pages Contexte et Visualisations."""
        if snapshot_id is None:
            snapshot_id = self.latest_snapshot()
        df = self.load_data(snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "snapshot_date": self.__date_snapshot(snapshot_id),
            "departements": self.__analyzer.departements(df),
            "kpi": self.__analyzer.kpi(df),
            "repartition_etiquettes": self.__analyzer.repartition_etiquettes(df),
            "conso_par_etiquette": self.__analyzer.conso_par_etiquette(df),
        }
