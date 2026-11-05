from pathlib import Path

import yaml

# Racine du projet, calculée à partir de ce fichier : le chemin reste juste
# quel que soit le dossier depuis lequel on lance le programme.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings():
    """Paramètres du projet.
    """

    def __init__(self):
        with open(PROJECT_ROOT / "config" / "tasks.yaml") as f:
            self.tasks: dict = yaml.safe_load(f)
