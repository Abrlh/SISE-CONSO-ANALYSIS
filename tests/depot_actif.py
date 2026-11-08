import pandas as pd


class DepotActif:
    """Imite DataRepository pour le snapshot actif et les données du formulaire."""

    def __init__(self, actif, modeles=None):
        self.actif = actif
        self.modeles = modeles or actif
        self.lus = []

    def snapshot_actif(self):
        return self.actif

    def modeles_actifs(self):
        return self.modeles

    def load_processed(self, snapshot_id):
        self.lus.append(snapshot_id)
        return {"59": pd.DataFrame({"a": [1.0, 3.0]})}
