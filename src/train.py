import argparse

from .data.repository import DataRepository
from .preprocessing import DataPreprocessor
from .models.registry import ModelRegistry


class TrainingPipeline():
    """
    Starting point for the training pipeline. 
    Responsible for orchestrating the training process, 
    including data loading, preprocessing, model training, and evaluation.
    """
    def __init__(self):

        self.__preprocessor:DataPreprocessor = DataPreprocessor()
        self.__repository:DataRepository = DataRepository()
        self.__registry:ModelRegistry = None
        tasks_config:dict
        pass

    # Étapes disponibles, toujours exécutées dans cet ordre
    STEPS = ("load", "preprocess")

    def run(self, steps:list[str], snapid:str|None=None, refresh:bool=False)-> dict:
        """
        Run the training pipeline for a given snapshot ID.

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
        if "load" in steps:
            print(f"=== Étape 1 : chargement des données brutes du snapshot {snapid} ===")
            datasets = self.load_raw(snapid)
        if "preprocess" in steps:
            print(f"=== Étape 2 : prétraitement des données brutes du snapshot {snapid} ===")
            self.preprocess(snapid, datasets)

        # 3 train model (snap id)

        # 4 evaluate model (snap id)

        # adapt task config


        pass


    def __resolve_snapshot(self, snapid:str|None, refresh:bool)-> str:
        """Renvoie l'id du snapshot à utiliser, en le téléchargeant si nécessaire."""
        print("=== Étape 0 ===")
        if refresh:
            print(f"    - actualisation du snapshot {snapid} ===")
            # -- refresh
            snapid = self.__repository.refresh(size=10)
        elif snapid is None:
            if not self.__repository.list_snapshots():
                #  en gros data/raw est vide, on télécharge un snapshot
                
                print(f"    - Étape 0 : téléchargement d'un snapshot ===")
                self.__repository.refresh(size=10)
            
            print(f"    - on récupère le dernier snapshot enregistré: {snapid}  ")
            snapid = self.__repository.latest_snapshot()
        return snapid


    ##########################
    # 1 load data
    def load_raw(self, snapid:str)-> dict:
        """Charge les données brutes du snapshot : {departement: {nom_dataset: DataFrame}}."""
        return self.__repository.load(snapid)


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
        self.__repository.save_processed(snapid, processed)
        return processed


if __name__ == "__main__":
    # Options de la ligne de commande, ex. : python -m src.train --refresh
    

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
    steps.add_argument("--preprocess", action="store_true",
                       help="prétraite les données brutes et enregistre le résultat dans data/processed/")

    
    
    
    args = parser.parse_args()

    # Liste des étapes demandées
    selected = []
    if args.load:
        selected.append("load")
    if args.preprocess:
        selected.append("preprocess")
    # Aucune étape demandée : on les lance toutes
    if not selected:
        selected = list(TrainingPipeline.STEPS)

    pipeline = TrainingPipeline()
    pipeline.run(steps=selected, snapid=args.snapshot, refresh=args.refresh)
    