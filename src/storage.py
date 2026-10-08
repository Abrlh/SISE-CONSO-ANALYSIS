
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


class Storage(ABC):
    @abstractmethod
    def save(self, obj, path)->None:
        pass

    @abstractmethod
    def load(self, path)->Any:
        pass



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
