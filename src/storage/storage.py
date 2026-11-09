
import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


class Storage(ABC):
    @abstractmethod
    def save(self, obj, path)->None:
        pass

    @abstractmethod
    def load(self, path)->Any:
        pass

    def alleger(self, path, colonnes, ecrire=True) -> tuple[int, int]:
        raise NotImplementedError


class LocalStorage(Storage):
    def __init__(self, root: str):
        super().__init__()
        self.root = Path(root)

    def save(self, obj: pd.DataFrame, path: str) -> None:
        full_path = self.root / path
        full_path.parent.mkdir(parents=True, exist_ok=True)  # crée le sous-dossier s'il n'existe pas
        obj.to_parquet(full_path)

    def load(self, path: str) -> pd.DataFrame:
        return pd.read_parquet(self.root / path)

    def alleger(self, path: str, colonnes: list[str], ecrire: bool = True) -> tuple[int, int]:
        """Réduit un fichier parquet aux colonnes demandées, en gardant leur ordre d'origine
        Returns:
            (nombre de colonnes avant, nombre de colonnes après)
        """
        full_path = self.root / path
        presentes = pq.read_schema(full_path).names
        absentes = sorted(set(colonnes) - set(presentes))
        if absentes:
            raise KeyError(f"colonnes absentes de {path} : {absentes}")
        a_garder = [c for c in presentes if c in set(colonnes)]
        if ecrire:
            df = pd.read_parquet(full_path, columns=a_garder)
            temporaire = full_path.with_suffix(".tmp")
            df.to_parquet(temporaire)
            temporaire.replace(full_path)
        return len(presentes), len(a_garder)


def supprimer_snapshots_anciens(root: Path, a_garder: list[str]) -> None:
    """Supprime dans root les dossiers de snapshot absents de a_garder et plus anciens que le plus récent gardé.

    Un snapshot plus récent est conservé : il peut être téléchargé et pas encore entraîné.
    Seuls les dossiers nommés comme un id de snapshot sont concernés.
    """
    for dossier in Path(root).iterdir():
        if (dossier.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{6}", dossier.name)
                and dossier.name not in a_garder and dossier.name < max(a_garder)):
            shutil.rmtree(dossier)
