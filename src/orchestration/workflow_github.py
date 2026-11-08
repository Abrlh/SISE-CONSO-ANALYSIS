import hmac
import os
from datetime import datetime

import requests


def mot_de_passe_valide(saisi:str)-> bool:
    """Compare la saisie à MOT_DE_PASSE_ADMIN ; toujours faux si la variable n'est pas définie."""
    attendu = os.environ.get("MOT_DE_PASSE_ADMIN")
    return bool(attendu) and hmac.compare_digest(saisi.encode(), attendu.encode())


class WorkflowGitHub():
    """Lance et suit le workflow de réentraînement (.github/workflows/retrain.yml) via l'API GitHub."""
    API = "https://api.github.com"
    WORKFLOW = "retrain.yml"
    TIMEOUT = 15

    def __init__(self, depot:str, token:str, branche:str="master"):
        self.__url = f"{self.API}/repos/{depot}/actions/workflows/{self.WORKFLOW}"
        self.__entetes = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        self.__branche = branche

    @classmethod
    def depuis_environnement(cls)-> "WorkflowGitHub | None":
        """Crée le client depuis les variables d'environnement, None s'il en manque une."""
        depot, token = os.environ.get("GITHUB_DEPOT"), os.environ.get("GITHUB_TOKEN")
        if not (depot and token and os.environ.get("MOT_DE_PASSE_ADMIN")):
            return None
        return cls(depot, token, os.environ.get("GITHUB_BRANCHE", "master"))

    def lancer(self)-> None:
        """Demande à GitHub de lancer le workflow sur la branche configurée."""
        requests.post(f"{self.__url}/dispatches", headers=self.__entetes, json={"ref": self.__branche},
                      timeout=self.TIMEOUT).raise_for_status()

    def dernier_run(self)-> dict|None:
        """Dernière exécution sur la branche : {id, statut, conclusion, url, cree_le}, None s'il n'y en a pas.

        cree_le a le format des id de snapshot : il se compare directement à une version de modèles.
        """
        reponse = requests.get(f"{self.__url}/runs", headers=self.__entetes,
                               params={"branch": self.__branche, "per_page": 1}, timeout=self.TIMEOUT)
        reponse.raise_for_status()
        runs = reponse.json()["workflow_runs"]
        if not runs:
            return None
        run = runs[0]
        cree_le = datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d_%H%M%S")
        return {"id": run["id"], "statut": run["status"], "conclusion": run["conclusion"],
                "url": run["html_url"], "cree_le": cree_le}
