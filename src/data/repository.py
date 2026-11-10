import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .api_client import AdemeApiClient
from ..storage.storage import LocalStorage, Storage, supprimer_snapshots_anciens

class DataRepository():
    NB_DEPARTEMENTS = 3
    # Format de l'id d'un snapshot : date et heure UTC du téléchargement, ex. "2026-10-08_143000".
    # Largeur fixe : l'ordre alphabétique des id est aussi l'ordre chronologique.
    SNAPSHOT_ID_FORMAT = "%Y-%m-%d_%H%M%S"

    def __init__(self, root:str|Path|None=None):
        #Load data-raw
        self.__client:AdemeApiClient = AdemeApiClient()
        # root : dossier des données brutes, data/raw par défaut (autre dossier pour les tests)
        self.__root = Path(root) if root is not None else Path(__file__).resolve().parent.parent.parent / "data" / "raw"
        self.__storage:Storage = LocalStorage(root=self.__root)

        # Données prétraitées : data/processed/<snapshot_id>/<departement>.parquet + meta.json
        self.__processed_root = self.__root.parent / "processed"
        self.__processed_storage:Storage = LocalStorage(root=self.__processed_root)

        # Snapshot affiché par l'application : data/snapshot_actif.json
        self.__actif_path = self.__root.parent / "snapshot_actif.json"

        self.__departements = self.__get_departements()
        # Statistiques pré-calculées : data/stats/<snapshot_id>/<nom>.parquet + meta.json
        self.__stats_root = self.__root.parent / "stats"
        self.__stats_storage:Storage = LocalStorage(root=self.__stats_root)

        pass


    def __get_departements(self)-> list:
        d = list()
        with open(self.__root / "codes_departements_nb_lignes.csv") as f:
            for i in range(self.NB_DEPARTEMENTS+1):
                line = f.readline()
                if line == "": raise ValueError(f"Le fichier codes_departements_nb_lignes.csv ne contient pas assez de lignes. Attendu: {self.NB_DEPARTEMENTS+1}, trouvé: {i}")
                code, nb_lignes = line.strip().split(",")
                if i == 0:continue  # skip header
                d.append(code)

        return d


    def refresh(self,size:int=10000,nb_page:int=10)-> str:
        """Télécharge les données de chaque département dans un nouveau snapshot.

        Arborescence créée :
            data/raw/<snapshot_id>/<departement>/<nom_dataset>.parquet
            data/raw/<snapshot_id>/meta.json

        Les fichiers parquet ne sont pas suivis par Git (.gitignore) : meta.json garde
        les noms des colonnes brutes pour l'audit du snapshot suivant.
        meta.json est écrit en dernier : s'il est absent, le téléchargement
        a été interrompu et le snapshot est ignoré par list_snapshots().

        Args:
            size: taille de page pour la requête
            nb_page: nombre maximum de pages à récupérer par dataset

        Returns:
            id du snapshot créé, ex. "2026-10-08_143000"
        """
        # Un seul id pour tout le téléchargement, généré avant la boucle
        snapshot_id = datetime.now(timezone.utc).strftime(self.SNAPSHOT_ID_FORMAT)
        contenu = {}  # {departement: [noms des datasets]}
        colonnes = set()  # noms des colonnes brutes, tous départements et datasets
        print("== Téléchargement des données ADEME ==")
        for departement in self.__departements:
            tps_debut = datetime.now() #TODO: delete ça
            print(f"    - Département {departement} ===")
            datasets = self.__client.get_full_datasets(code_departement=departement,size=size,nb_page=nb_page)
            for name, df in datasets.items():
                self.__storage.save(df, path=f"{snapshot_id}/{departement}/{name}.parquet")
                colonnes.update(df.columns)
            contenu[departement] = list(datasets.keys())
            tps_fin = datetime.now() #TODO: delete ça 
            print(f"      -> {len(datasets)} datasets téléchargés en {tps_fin - tps_debut}")

        meta = {"snapshot_id": snapshot_id, "departements": contenu, "colonnes": sorted(colonnes)}
        snapshot_dir = self.__root / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        return snapshot_id

    def departements(self)-> list[str]:
        """Codes des départements traités par le projet."""
        return list(self.__departements)


    def snapshot_actif(self)-> str|None:
        """Id du snapshot affiché par l'application, None si aucun n'a encore été publié."""
        if not self.__actif_path.exists():
            return None
        return json.loads(self.__actif_path.read_text())["snapshot_id"]


    def modeles_actifs(self)-> str|None:
        """Id de la version de modèles affichée par l'application, None si aucune n'a encore été publiée."""
        if not self.__actif_path.exists():
            return None
        return json.loads(self.__actif_path.read_text())["modeles_id"]


    def definir_snapshot_actif(self, snapshot_id:str, modeles_id:str)-> None:
        """Publie un snapshot de données et une version de modèles.
        Écriture atomique : l'application lit l'ancienne publication ou la nouvelle, jamais un fichier partiel."""
        temporaire = self.__actif_path.with_suffix(".tmp")
        temporaire.write_text(json.dumps({"snapshot_id": snapshot_id, "modeles_id": modeles_id}, indent=2))
        temporaire.replace(self.__actif_path)


    def remove_old_snapshots(self, a_garder:list[str])-> None:
        """Supprime les anciens snapshots de data/raw, data/processed et data/stats.

        Args:
            a_garder: id des snapshots à conserver (voir supprimer_snapshots_anciens)
        """
        for root in (self.__root, self.__processed_root, self.__stats_root):
            supprimer_snapshots_anciens(root, a_garder)


    def list_snapshots(self)-> list[str]:
        """Renvoie les id des snapshots complets, du plus ancien au plus récent.

        Seuls les dossiers contenant meta.json sont retenus.
        """
        return sorted(p.name for p in self.__root.iterdir() if (p / "meta.json").exists())


    def latest_snapshot(self)-> str:
        """Renvoie l'id du snapshot complet le plus récent.

        Raises:
            FileNotFoundError: aucun snapshot complet dans data/raw
        """
        snapshots = self.list_snapshots()
        if not snapshots:
            raise FileNotFoundError("Aucun snapshot complet dans data/raw. Lancez d'abord : python -m src.orchestration.refresh")
        return snapshots[-1]


    def load(self, snapshot_id:str)-> dict[str, pd.DataFrame]:
        """Recharge un snapshot.

        Args:
            snapshot_id: id du snapshot, ex. "2026-10-08_143000"

        Returns:
            {departement: [{dataset_name: DataFrame}]}, les datasets étant séparés par département

        Raises:
            FileNotFoundError: fichiers parquet absents (ils ne sont pas dans le dépôt Git)
        """
        meta = json.loads((self.__root / snapshot_id / "meta.json").read_text())
        frames = {}  # {nom_dataset: [DataFrame de chaque département]}
        for departement, names in meta["departements"].items():
            frames[departement] = {}
            for name in names:
                if not (self.__root / snapshot_id / departement / f"{name}.parquet").exists():
                    raise FileNotFoundError(f"Données brutes du snapshot {snapshot_id} absentes : elles ne sont pas dans le dépôt Git. "
                                            "Lancez : python -m src.orchestration.train --refresh")
                df = self.__storage.load(path=f"{snapshot_id}/{departement}/{name}.parquet")
                frames[departement][name] = df
        return frames
    def save_processed(self, snapshot_id:str, data:dict[str, pd.DataFrame], nettoyage:dict|None=None)-> None:
        """Enregistre les données prétraitées d'un snapshot.

        Arborescence créée :
            data/processed/<snapshot_id>/<departement>.parquet
            data/processed/<snapshot_id>/meta.json

        meta.json est supprimé avant l'écriture et réécrit en dernier : si l'écriture
        est interrompue, le dossier est considéré comme absent par load_processed().

        Args:
            snapshot_id: id du snapshot brut dont proviennent les données
            data: {departement: DataFrame}
        """

        processed_dir = self.__processed_root / snapshot_id
        processed_dir.mkdir(parents=True, exist_ok=True)
        (processed_dir / "meta.json").unlink(missing_ok=True)
        for departement, df in data.items():
            self.__processed_storage.save(df, path=f"{snapshot_id}/{departement}.parquet")
        meta = {"snapshot_id": snapshot_id, "departements": list(data)}
        if nettoyage is not None:
            meta["nettoyage"] = nettoyage
        (processed_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    def load_nettoyage(self, snapshot_id:str)-> dict:
        """Rapport du nettoyage enregistré avec les données nettoyées ({} s'il n'y en a pas)."""
        meta_path = self.__processed_root / snapshot_id / "meta.json"
        if not meta_path.exists():
            return {}
        return json.loads(meta_path.read_text()).get("nettoyage", {})

    def load_processed(self, snapshot_id:str)-> dict[str, pd.DataFrame]:
        """Recharge les données prétraitées d'un snapshot.

        Returns:
            {departement: DataFrame}

        Raises:
            FileNotFoundError: pas de données prétraitées complètes pour ce snapshot
        """
        meta_path = self.__processed_root / snapshot_id / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Pas de données prétraitées pour le snapshot {snapshot_id}. Lancez : python -m src.orchestration.train --preprocess")
        departements = json.loads(meta_path.read_text())["departements"]
        return {d: self.__processed_storage.load(path=f"{snapshot_id}/{d}.parquet") for d in departements}

    def alleger_processed(self, snapshot_id:str, colonnes:dict[str, list[str]], ecrire:bool=True)-> dict[str, tuple[int, int]]:
        """Réduit les données prétraitées d'un snapshot aux colonnes demandées. """
        return {d: self.__processed_storage.alleger(f"{snapshot_id}/{d}.parquet", cols, ecrire=ecrire)
                for d, cols in colonnes.items()}

    
    def save_stats(self, snapshot_id:str, stats:dict[str, pd.DataFrame])-> None:
        """Enregistre les statistiques pré-calculées d'un snapshot.

        Arborescence créée :
            data/stats/<snapshot_id>/<nom_stat>.parquet
            data/stats/<snapshot_id>/meta.json

        meta.json est supprimé avant l'écriture et réécrit en dernier : si l'écriture
        est interrompue, le dossier est considéré comme absent par list_stats().

        Args:
            snapshot_id: id du snapshot dont proviennent les statistiques
            stats: {nom_stat: DataFrame}
        """
        stats_dir = self.__stats_root / snapshot_id
        stats_dir.mkdir(parents=True, exist_ok=True)
        (stats_dir / "meta.json").unlink(missing_ok=True)
        for name, df in stats.items():
            self.__stats_storage.save(df, path=f"{snapshot_id}/{name}.parquet")
        meta = {"snapshot_id": snapshot_id, "stats": list(stats),
                "calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        (stats_dir / "meta.json").write_text(json.dumps(meta, indent=2))


    def colonnes(self, snapshot_id:str)-> set[str]:
        """Noms des colonnes d'un snapshot brut (tous départements et datasets).
        Lus dans meta.json : les fichiers parquet ne sont pas dans le dépôt Git."""
        return set(json.loads((self.__root / snapshot_id / "meta.json").read_text())["colonnes"])


    def snapshot_precedent(self, snapshot_id:str)-> str|None:
        """Id du snapshot complet juste avant snapshot_id, None s'il n'y en a pas."""
        avant = [s for s in self.list_snapshots() if s < snapshot_id]
        return avant[-1] if avant else None


    def save_audit(self, snapshot_id:str, audit:pd.DataFrame)-> Path:
        """Enregistre l'audit des colonnes d'un snapshot dans docs/audit_<snapshot_id>.csv.

        Args:
            snapshot_id: id du snapshot audité
            audit: description des colonnes nouvelles (renvoyée par audit_colonnes.auditer)

        Returns:
            chemin du fichier écrit
        """
        sortie = self.__root.parent.parent / "docs" / f"audit_{snapshot_id}.csv"
        audit.to_csv(sortie, index=False)
        return sortie


    def list_stats(self, snapshot_id:str)-> list[str]:
        """Renvoie les noms des statistiques disponibles pour un snapshot.

        Raises:
            FileNotFoundError: pas de statistiques complètes pour ce snapshot
        """
        meta_path = self.__stats_root / snapshot_id / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Pas de statistiques pour le snapshot {snapshot_id}. Lancez : python -m src.orchestration.train --snapshot {snapshot_id} --stats")
        return json.loads(meta_path.read_text())["stats"]


    def load_stat(self, snapshot_id:str, name:str)-> pd.DataFrame:
        """Relit une statistique pré-calculée.

        Raises:
            FileNotFoundError: pas de statistiques pour ce snapshot
            KeyError: statistique inconnue
        """
        if name not in self.list_stats(snapshot_id):
            raise KeyError(f"Statistique inconnue : {name}. Disponibles : {self.list_stats(snapshot_id)}")
        return self.__stats_storage.load(path=f"{snapshot_id}/{name}.parquet")

    
    def list_stats_snapshots(self)-> list[str]:
        """Renvoie les id des snapshots qui ont des statistiques complètes, du plus ancien
        au plus récent (seuls les dossiers contenant meta.json sont retenus)."""
        if not self.__stats_root.exists():
            return []
        return sorted(p.name for p in self.__stats_root.iterdir() if (p / "meta.json").exists())