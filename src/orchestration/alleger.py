"""Allège les données pour l'image Docker (Render gratuit : 512 Mo) et pour le dépôt Git
(workflow de réentraînement, avant le commit).

Garde uniquement le snapshot de données et la version de modèles publiés dans
data/snapshot_actif.json, et réduit data/processed aux colonnes utilisées par les modèles.

Exemples :
    python -m src.orchestration.alleger            # simulation, rien n'est modifié
    ALLEGER_ECRITURE=1 python -m src.orchestration.alleger --ecrire   # image Docker, workflow GitHub
"""
import argparse
import os

from ..data.repository import DataRepository
from ..models.registry import ModelRegistry


class AllegementImage():
    """Prépare data/ et models/ pour l'image de l'application."""
    # tâches pour lesquelles un modèle est enregistré par département
    TACHES = ("classification", "regression")

    def __init__(self, repository:DataRepository|None=None, registry:ModelRegistry|None=None):
        self.__repository:DataRepository = repository or DataRepository()
        self.__registry:ModelRegistry = registry or ModelRegistry()

    def snapshots_publies(self)-> tuple[str, str]:
        """(snapshot de données, version de modèles) affichés par l'application.

        Raises:
            FileNotFoundError: rien n'est publié (data/snapshot_actif.json absent)
            ValueError: la version de modèles n'a pas été entraînée sur le snapshot publié
        """
        donnees = self.__repository.snapshot_actif()
        modeles = self.__repository.modeles_actifs()
        if donnees is None or modeles is None:
            raise FileNotFoundError("data/snapshot_actif.json absent : aucun snapshot n'est publié.")
        source = self.__registry.snapshot_source(modeles)
        if source != donnees:
            raise ValueError(f"Les modèles {modeles} viennent du snapshot {source}, "
                             f"mais le snapshot publié est {donnees}.")
        return donnees, modeles

    def colonnes_utiles(self, modeles:str)-> dict[str, set[str]]:
        """{departement: colonnes utilisées par les modèles de la version, cibles comprises}."""
        utiles = {}
        for tache in self.TACHES:
            for departement in self.__registry.list_departements(tache, modeles):
                meta = self.__registry.load_meta(tache, departement, modeles)
                colonnes = utiles.setdefault(departement, set())
                colonnes.update(meta["colonnes"])
                if meta.get("cible"):
                    colonnes.add(meta["cible"])
        return utiles

    def alleger(self, ecrire:bool=False)-> None:
        """Réduit les données prétraitées et supprime les autres snapshots (voir le haut du fichier).

        Args:
            ecrire: False (par défaut) pour simuler. True modifie les fichiers et n'est
                accepté que pendant la construction de l'image et dans le workflow GitHub
                (variable ALLEGER_ECRITURE=1).
        """
        if ecrire and os.environ.get("ALLEGER_ECRITURE") != "1":
            raise PermissionError("--ecrire modifierait les fichiers du dépôt : "
                                  "réservé à la construction de l'image et au workflow GitHub (ALLEGER_ECRITURE=1).")
        donnees, modeles = self.snapshots_publies()
        print(f"Snapshot de données publié : {donnees}")
        print(f"Version de modèles publiée : {modeles}")
        colonnes = self.colonnes_utiles(modeles)
        if not colonnes:
            raise FileNotFoundError(f"Aucun modèle trouvé dans models/{modeles}.")
        resultats = self.__repository.alleger_processed(donnees, {d: sorted(c) for d, c in colonnes.items()},
                                                        ecrire=ecrire)
        for departement, (avant, apres) in sorted(resultats.items()):
            print(f"    - département {departement} : {avant} colonnes -> {apres}")
        if ecrire:
            self.__repository.remove_old_snapshots([donnees])
            self.__registry.remove_old_snapshots([modeles])
            print("Terminé : anciens snapshots supprimés, données allégées.")
        else:
            print("Simulation : rien n'a été modifié.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Allège les données pour l'image Docker.")
    parser.add_argument("--ecrire", action="store_true",
                        help="modifie les fichiers (construction de l'image uniquement)")
    args = parser.parse_args()
    AllegementImage().alleger(ecrire=args.ecrire)