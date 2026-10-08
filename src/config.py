from pathlib import Path

import yaml

# Racine du projet, calculée à partir de ce fichier : le chemin reste juste
# quel que soit le dossier depuis lequel on lance le programme.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings():
    """Paramètres du projet.

    Lit config/tasks.yaml à la création et expose son contenu dans
    `self.tasks`, un dict Python ordinaire.

    Exemple d'utilisation (dans TrainingPipeline par exemple) :

        settings = Settings()

        clf = settings.tasks["classification"]
        clf["target"]     # nom de la colonne à prédire, ex. "etiquette_dpe"
        clf["estimator"]  # nom de la classe scikit-learn, ex. "RandomForestClassifier"
        clf["params"]     # dict d'hyperparamètres, ex. {"n_estimators": 200}

        # Création de l'estimateur à partir de son nom :
        from sklearn.ensemble import RandomForestClassifier
        ESTIMATORS = {"RandomForestClassifier": RandomForestClassifier}
        model = ESTIMATORS[clf["estimator"]](**clf["params"])
        # équivaut à RandomForestClassifier(n_estimators=200)

        y = df[clf["target"]]
        X = df.drop(columns=[clf["target"]])
    """

    def __init__(self):
        with open(PROJECT_ROOT / "config" / "tasks.yaml") as f:
            self.tasks: dict = yaml.safe_load(f)
