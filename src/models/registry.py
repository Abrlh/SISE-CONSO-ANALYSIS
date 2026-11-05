import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn

from .base import BaseModel


class ModelRegistry():
    """Enregistre, recharge et décrit les modèles entraînés.

    Arborescence :
        models/<snapshot_id>/<tache>/<departement>/model.joblib
        models/<snapshot_id>/<tache>/<departement>/evaluation/<nom>.parquet   (données de performance pour le front)
        models/<snapshot_id>/<tache>/<departement>/meta.json   (écrit en dernier)

    Un dossier sans meta.json correspond à un enregistrement interrompu et est ignoré.
    Attention : joblib.load peut exécuter du code, ne charger que des modèles produits par le projet.
    """


    def __init__(self, root:str|Path|None=None):
        # root : dossier des modèles, models/ à la racine du projet par défaut (autre dossier pour les tests)
        self.__root = Path(root) if root is not None else Path(__file__).resolve().parent.parent.parent / "models"
        pass

    def save(self, tache:str, departement:str, snapid:str, model:BaseModel, metadata:dict[str, Any],
             evaluation:dict[str, pd.DataFrame]|None=None)-> Path:
        """Enregistre un modèle, ses métadonnées et ses tableaux de performance.

        Args:
            tache: ex. "classification"
            departement: ex. "75"
            snapid: id du snapshot sur lequel le modèle a été entraîné
            model: modèle entraîné (objet entier : predict() et evaluate() restent disponibles au chargement)
            metadata: informations à garder dans meta.json (cible, colonnes, métriques...)
            evaluation: {nom: DataFrame} de model.tableaux_evaluation(), écrits dans evaluation/<nom>.parquet

        Returns:
            dossier du modèle
        """
        dossier = self.__root / snapid / tache / departement
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "meta.json").unlink(missing_ok=True)
        joblib.dump(model, dossier / "model.joblib")
        evaluation = evaluation or {}
        (dossier / "evaluation").mkdir(exist_ok=True)
        for nom, df in evaluation.items():
            df.to_parquet(dossier / "evaluation" / f"{nom}.parquet", index=False)
        meta = {"snapshot_id": snapid, "tache": tache, "departement": departement,
                "modele": type(model).__name__, "sklearn_version": sklearn.__version__,
                "entraine_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "evaluation": list(evaluation),
                **metadata}
        # default=float : les scores scikit-learn peuvent être des types numpy
        (dossier / "meta.json").write_text(json.dumps(meta, indent=2, default=float))
        return dossier

    def load(self, tache:str, departement:str, snapid:str|None=None)-> BaseModel:
        """Charge un modèle, celui du snapshot le plus récent par défaut.

        Raises:
            FileNotFoundError: aucun modèle enregistré pour cette tâche et ce département
        """
        meta = self.load_meta(tache, departement, snapid)
        if meta["sklearn_version"] != sklearn.__version__:
            warnings.warn(f"Modèle entraîné avec scikit-learn {meta['sklearn_version']}, "
                          f"version installée {sklearn.__version__} : réentraîner le modèle.")
        return joblib.load(self.__root / meta["snapshot_id"] / tache / departement / "model.joblib")

    def load_meta(self, tache:str, departement:str, snapid:str|None=None)-> dict:
        """Renvoie le contenu de meta.json, celui du snapshot le plus récent par défaut."""
        if snapid is None:
            snapshots = self.list_snapshots(tache, departement)
            if not snapshots:
                raise FileNotFoundError(f"Aucun modèle {tache} pour le département {departement}. "
                                        f"Lancez : python -m src.orchestration.train --train")
            snapid = snapshots[-1]
        return json.loads((self.__root / snapid / tache / departement / "meta.json").read_text())

    def load_evaluation(self, tache:str, departement:str, nom:str, snapid:str|None=None)-> pd.DataFrame:
        """Relit un tableau de performance (ex. "scores", "matrice_confusion"), du snapshot le plus récent par défaut.

        Raises:
            KeyError: tableau inconnu pour ce modèle (le message liste ceux disponibles)
        """
        meta = self.load_meta(tache, departement, snapid)
        if nom not in meta.get("evaluation", []):
            raise KeyError(f"Tableau {nom!r} absent pour {tache} {departement}. "
                           f"Disponibles : {meta.get('evaluation', [])}")
        return pd.read_parquet(self.__root / meta["snapshot_id"] / tache / departement / "evaluation" / f"{nom}.parquet")

    def list_snapshots(self, tache:str, departement:str)-> list[str]:
        """Id des snapshots qui ont un modèle complet pour cette tâche et ce département, du plus ancien au plus récent."""
        if not self.__root.exists():
            return []
        return sorted(p.name for p in self.__root.iterdir()
                      if (p / tache / departement / "meta.json").exists())

    def list_departements(self, tache:str)-> list[str]:
        """Départements qui ont au moins un modèle complet pour cette tâche."""
        if not self.__root.exists():
            return []
        return sorted({p.parent.name for p in self.__root.glob(f"*/{tache}/*/meta.json")})
