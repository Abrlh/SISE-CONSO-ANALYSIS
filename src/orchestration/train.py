import argparse
from datetime import datetime, timezone

import pandas as pd
from sklearn.model_selection import train_test_split

from ..data.repository import DataRepository
from ..processing.audit_colonnes import auditer, afficher
from ..processing.preprocessing import DataPreprocessor
from ..processing.analysis import StatAnalyzer
from ..models.registry import ModelRegistry
from ..models.classification import ClassificationModel
from ..models.regression import RegressionModel
from ..models.features import CIBLE_CLASSIFICATION, CIBLE_REGRESSION, preparer_xy


class TrainingPipeline():
    """Pipeline d'entraînement : chargement, audit, prétraitement, statistiques, entraînement."""
    def __init__(self):

        self.__preprocessor:DataPreprocessor = DataPreprocessor()
        self.__repository:DataRepository = DataRepository()
        self.__analyzer:StatAnalyzer = StatAnalyzer()
        self.__registry:ModelRegistry = ModelRegistry()
        tasks_config:dict
        pass

    # Étapes disponibles, toujours exécutées dans cet ordre
    STEPS = ("load", "audit", "preprocess", "stats", "train")
    NB_SNAPSHOTS_GARDES = 2

    def run(self, steps:list[str], snapid:str|None=None, refresh:bool=False)-> dict:
        """Lance les étapes demandées du pipeline sur un snapshot.

        Args:
            steps: étapes à exécuter, parmi STEPS
            snapid: id du snapshot à utiliser (ex. "2026-10-08_143000"), None pour le plus récent
            refresh: True pour télécharger un nouveau snapshot avant l'entraînement

        Sans snapid ni refresh, le dernier snapshot est réutilisé : l'API n'est
        appelée que si aucun snapshot complet n'existe encore.
        Chaque étape lancée seule relit ce dont elle a besoin sur le disque.
        """
        snapid = self.__resolve_snapshot(snapid, refresh)  # snapid à enregistrer dans metadata.json

        datasets = None
        processed = None
        if "load" in steps:
            print(f"=== Étape 1 : chargement des données brutes du snapshot {snapid} ===")
            datasets = self.load_raw(snapid)
        if "audit" in steps:
            print(f"=== Étape 1 bis : audit des colonnes du snapshot {snapid} ===")
            # chargées ici pour que preprocess les réutilise sans relire le disque
            if datasets is None:
                datasets = self.load_raw(snapid)
            self.audit(snapid, datasets)
        if "preprocess" in steps:
            print(f"=== Étape 2 : prétraitement des données brutes du snapshot {snapid} ===")
            processed = self.preprocess(snapid, datasets)
        if "stats" in steps:
            print(f"=== Étape 3 : calcul des statistiques du snapshot {snapid} ===")
            self.stats(snapid, processed)
        if "train" in steps:
            print(f"=== Étape 4 : entraînement et évaluation des modèles du snapshot {snapid} ===")
            self.train(snapid, processed, self.__version_modeles(snapid))
            self.__publier_et_nettoyer_snapshots()

        # adapt task config


        pass


    def __resolve_snapshot(self, snapid:str|None, refresh:bool)-> str:
        """Renvoie l'id du snapshot à utiliser, en le téléchargeant si nécessaire."""
        print("=== Étape 0 ===")
        if refresh:
            print(f"    - actualisation du snapshot {snapid} ===")
            # -- refresh
            snapid = self.__repository.refresh(size=10000)
        elif snapid is None:
            if not self.__repository.list_snapshots():
                #  en gros data/raw est vide, on télécharge un snapshot
                
                print(f"    - Étape 0 : téléchargement d'un snapshot ===")
                self.__repository.refresh(size=10000)
            
            snapid = self.__repository.latest_snapshot()
            print(f"    - on récupère le dernier snapshot enregistré: {snapid}  ")
        return snapid


    def __versions_abouties(self)-> list[str]:
        """Versions de modèles complètes dont le snapshot source a ses statistiques, de la plus ancienne à la plus récente."""
        stats = self.__repository.list_stats_snapshots()
        return [v for v in self.__registry.snapshots_complets(list(self.TACHES), self.__repository.departements())
                if self.__registry.snapshot_source(v) in stats]


    def __version_modeles(self, snapid:str)-> str:
        """Renvoie la version de modèles à écrire : un nouvel id si snapid est affiché par l'application, snapid sinon.

        L'application continue de lire les anciens modèles jusqu'à la publication de la nouvelle version.
        """
        aboutis = self.__versions_abouties()
        if self.__repository.snapshot_actif() is None and aboutis:
            # sans pointeur, l'application lirait la nouvelle version, plus récente, pendant son écriture
            self.__repository.definir_snapshot_actif(self.__registry.snapshot_source(aboutis[-1]), aboutis[-1])
        if snapid != self.__repository.snapshot_actif():
            return snapid
        return datetime.now(timezone.utc).strftime(self.__repository.SNAPSHOT_ID_FORMAT)


    def __versions_a_garder(self)-> list[str]:
        """Versions de modèles à conserver, de la plus ancienne à la plus récente.

        Les NB_SNAPSHOTS_GARDES dernières (l'application lancée lit peut-être l'avant-dernière), plus la dernière
        version de chacun des NB_SNAPSHOTS_GARDES derniers snapshots de données : réentraîner plusieurs fois
        le même snapshot ne fait donc jamais disparaître le téléchargement précédent.
        """
        aboutis = self.__versions_abouties()
        derniere_par_source = {self.__registry.snapshot_source(v): v for v in aboutis}
        sources = sorted(derniere_par_source)[-self.NB_SNAPSHOTS_GARDES:]
        return sorted({*aboutis[-self.NB_SNAPSHOTS_GARDES:], *(derniere_par_source[s] for s in sources)})


    def __publier_et_nettoyer_snapshots(self)-> None:
        """Publie la dernière version de modèles aboutie, puis supprime de data/raw, data/processed, data/stats
        et models/ les snapshots plus anciens que ceux à conserver (voir __versions_a_garder)."""
        a_garder = self.__versions_a_garder()
        if not a_garder:
            return
        sources = [self.__registry.snapshot_source(v) for v in a_garder]
        # publié avant la suppression : l'application ne pointe jamais vers un dossier supprimé
        self.__repository.definir_snapshot_actif(sources[-1], a_garder[-1])
        self.__repository.remove_old_snapshots(sources)
        self.__registry.remove_old_snapshots(a_garder)
        print(f"=== Nettoyage : snapshots conservés : {a_garder} ===")


    ##########################
    # 1 load data
    def load_raw(self, snapid:str)-> dict:
        """Charge les données brutes du snapshot : {departement: {nom_dataset: DataFrame}}."""
        return self.__repository.load(snapid)


    ##########################
    # 1 bis audit des colonnes
    def audit(self, snapid:str, datasets:dict|None=None)-> tuple:
        """Contrôle les colonnes du snapshot (voir src/processing/audit_colonnes.py).

        Args:
            snapid: id du snapshot
            datasets: données brutes déjà chargées par load_raw(), None pour les charger ici

        Returns:
            (manquantes : {colonne: [usages]}, nouvelles : DataFrame, disparues : liste)
        """
        if datasets is None:
            datasets = self.load_raw(snapid)
        tout = pd.concat([d for dep in datasets.values() for d in dep.values()], ignore_index=True)
        precedent = self.__repository.snapshot_precedent(snapid)
        colonnes_precedentes = self.__repository.colonnes(precedent) if precedent else None
        manquantes, desc, disparues = auditer(tout, colonnes_precedentes)
        sortie = self.__repository.save_audit(snapid, desc) if len(desc) else None
        afficher(snapid, tout, manquantes, desc, disparues, precedent, sortie)
        return manquantes, desc, disparues


    ##########################
    # 2 preprocess data
    def preprocess(self, snapid:str, datasets:dict|None=None)-> dict:
        """Prétraite les données brutes du snapshot et enregistre le résultat.

        Args:
            snapid: id du snapshot
            datasets: données brutes déjà chargées par load_raw(), None pour les charger ici

        Returns:
            {departement: DataFrame}, existants et neufs fusionnés
        """
        if datasets is None:
            datasets = self.load_raw(snapid)

        # TODO: PREPROCESSING ICI, TU PEUX LOAD DIRECTEMENT LES DONNEES
        
        
        ####################################################
        
        
        list_departements = list(datasets.keys())


        #####################################################
        print("    - A SUPPRIMER : Exemple pour accéder aux données enregistrées dans data/raw")
        for departement in list_departements:
            print(f"        - Departement {departement} ===")
            
            # dataframe avec les données brutes:
            df_dpe_existants = datasets[departement]["dpe_existants"]

            df_dpe_neufs = datasets[departement]["dpe_neufs"]
            
            
            print(f"          -> dpe_existants : nb lignes : {len(df_dpe_existants)}, nb colonnes : {len(df_dpe_existants.columns)}")

            print(f"          -> dpe_neufs : nb lignes : {len(df_dpe_neufs)}, nb colonnes : {len(df_dpe_neufs.columns)}")
        
        ####################################################

        # TODO: DataPreprocessor.process(datasets) à écrire, doit renvoyer {departement: DataFrame}
        processed = self.__preprocessor.process(datasets)
        
        # on enregistre les données prétraitées dans data/processed/<snapid>/<departement>.parquet
        self.__repository.save_processed(snapid, processed, self.__preprocessor.rapport())
        return processed

    ##########################
    # 3 statistiques pré-calculées pour l'application
    def stats(self, snapid:str, processed:dict|None=None)-> dict:
        """Calcule les analyses statistiques et les enregistre dans data/stats/<snapid>/.

        Args:
            snapid: id du snapshot
            processed: données propres déjà chargées, None pour les relire sur le disque

        Returns:
            {nom_analyse: DataFrame}
        """
        if processed is None:
            processed = self.__repository.load_processed(snapid)
        stats = self.__analyzer.compute_all(processed, self.__repository.load_nettoyage(snapid))
        self.__repository.save_stats(snapid, stats)
        return stats

    ##########################
    # 4 entraînement et évaluation (un modèle par tâche et par département)
    # {tâche: (classe du modèle, colonne à prédire)}
    TACHES = {"classification": (ClassificationModel, CIBLE_CLASSIFICATION),
              "regression": (RegressionModel, CIBLE_REGRESSION)}

    def train(self, snapid:str, processed:dict|None=None, version:str|None=None)-> dict:
        """Entraîne, évalue et enregistre un modèle par tâche et par département.

        Args:
            snapid: id du snapshot
            processed: données propres déjà chargées, None pour les relire sur le disque
            version: dossier de models/ où écrire, None pour utiliser snapid

        Returns:
            {(tache, departement): métriques sur le jeu de test}
        """
        if processed is None:
            processed = self.__repository.load_processed(snapid)
        resultats = {}
        for departement, df in processed.items():
            print(f"    - Département {departement} : {len(df)} lignes")
            # même découpage pour les deux tâches : les mêmes logements servent de test
            train_idx, test_idx = train_test_split(df.index, test_size=0.3, random_state=42)
            for tache, (classe, cible) in self.TACHES.items():
                X, y = preparer_xy(df, cible)
                modele = classe()
                modele.train(X.loc[train_idx], y.loc[train_idx])
                metriques = modele.evaluate(X.loc[test_idx], y.loc[test_idx])
                scores = ", ".join(f"{k} : {v:.3f}" for k, v in metriques.items() if k != "rapport")
                print(f"      {tache} : {scores}" + (f" ({modele.meilleurs_params})" if modele.meilleurs_params else ""))
                # données de performance pour le front (scores, matrice de confusion, importance...)
                evaluation = modele.tableaux_evaluation(X.loc[test_idx], y.loc[test_idx], y.loc[train_idx])
                self.__registry.save(tache, departement, version or snapid, modele, {
                    "snapshot_source": snapid,
                    "cible": cible,
                    "colonnes": list(X.columns),
                    "meilleurs_params": modele.meilleurs_params,
                    "nb_lignes_train": len(train_idx), "nb_lignes_test": len(test_idx),
                    "metriques_test": metriques,
                }, evaluation)
                resultats[(tache, departement)] = metriques
        return resultats


if __name__ == "__main__":
    # Options de la ligne de commande, ex. : python -m src.orchestration.train --refresh
    

    parser = argparse.ArgumentParser(description="Entraîne les modèles à partir d'un snapshot des données ADEME.")
    # --refresh et --snapshot s'excluent : on télécharge un nouveau snapshot OU on en choisit un existant
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--refresh", action="store_true",
                        help="télécharge un nouveau snapshot avant l'entraînement")
    source.add_argument("--snapshot",
                        help="id du snapshot à utiliser, ex. 2026-10-08_175824 (par défaut : le plus récent)")
    
    
    
    # Une option par étape, cumulables. Sans option d'étape, toutes les étapes sont lancées.
    steps = parser.add_argument_group("étapes (par défaut : toutes)")
    steps.add_argument("--load", action="store_true",
                       help="charge les données brutes (avec --refresh : télécharge un nouveau snapshot)")
    steps.add_argument("--audit", action="store_true",
                       help="repère les colonnes nouvelles ou disparues du snapshot (écrit docs/audit_<snapshot>.csv)")
    steps.add_argument("--preprocess", action="store_true",
                       help="prétraite les données brutes et enregistre le résultat dans data/processed/")
    steps.add_argument("--stats", action="store_true",
                        help="calcule les statistiques pré-calculées pour l'application et les enregistre dans data/stats/")
    steps.add_argument("--train", action="store_true",
                       help="entraîne les modèles (classification et régression) par département et les enregistre dans models/")
    
    
    
    args = parser.parse_args()

    # Liste des étapes demandées
    selected = []
    if args.load:
        selected.append("load")
    if args.audit:
        selected.append("audit")
    if args.preprocess:
        selected.append("preprocess")
    if args.stats:
        selected.append("stats")
    if args.train:
        selected.append("train")
    # Aucune étape demandée : on les lance toutes
    if not selected:
        selected = list(TrainingPipeline.STEPS)

    pipeline = TrainingPipeline()
    pipeline.run(steps=selected, snapid=args.snapshot, refresh=args.refresh)
    