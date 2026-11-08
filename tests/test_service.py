"""
Tests unitaires du service de l'application (src/orchestration/service.py) : lecture des statistiques.
On utilise un faux dépôt en mémoire : aucun fichier n'est lu.

Lancer : python -m pytest tests/test_service.py -v
"""
import pandas as pd
import pytest

from src.orchestration.service import AppService


class FauxDepot:
    """Imite DataRepository pour les statistiques : {snapshot: {nom: DataFrame}}."""

    def __init__(self, stats):
        self.stats = stats
        self.lectures = 0            # nombre de lectures "disque"
        self.actif = None

    def snapshot_actif(self):
        return self.actif

    def modeles_actifs(self):
        return self.actif

    def list_stats_snapshots(self):
        return sorted(self.stats)

    def list_stats(self, snapshot_id):
        return list(self.stats[snapshot_id])

    def load_stat(self, snapshot_id, name):
        if name not in self.stats[snapshot_id]:
            raise KeyError(f"Statistique inconnue : {name}")
        self.lectures += 1
        return self.stats[snapshot_id][name]


def depot():
    return FauxDepot({
        "2026-10-08_100000": {"kpi": pd.DataFrame({"x": [1]})},
        "2026-10-12_132605": {"kpi": pd.DataFrame({"x": [1, 2, 3]}), "communes": pd.DataFrame({"y": [9]})},
    })


def test_utilise_le_snapshot_le_plus_recent():
    service = AppService(repository=depot())
    assert service.snapshot_stats() == "2026-10-12_132605"
    assert service.liste_stats() == ["kpi", "communes"]
    assert len(service.get_stat("kpi")) == 3


def test_lecture_unique_puis_cache():
    d = depot()
    service = AppService(repository=d)
    service.get_stat("kpi")
    service.get_stat("kpi")
    service.get_stat("kpi")
    assert d.lectures == 1


def test_get_stat_renvoie_une_copie():
    service = AppService(repository=depot())
    t = service.get_stat("kpi")
    t["x"] = 0                                      # une page modifie son tableau
    t.loc[len(t)] = 99
    assert service.get_stat("kpi")["x"].tolist() == [1, 2, 3]


def test_statistique_inconnue():
    service = AppService(repository=depot())
    with pytest.raises(KeyError):
        service.get_stat("n_existe_pas")


def test_aucune_statistique_calculee_message_clair():
    service = AppService(repository=FauxDepot({}))
    with pytest.raises(FileNotFoundError, match="--stats"):
        service.snapshot_stats()


def test_recharger_stats_prend_un_nouveau_snapshot():
    d = depot()
    service = AppService(repository=d)
    assert service.snapshot_stats() == "2026-10-12_132605"
    d.stats["2026-10-20_090000"] = {"kpi": pd.DataFrame({"x": [7, 7, 7, 7]})}
    assert service.snapshot_stats() == "2026-10-12_132605"      # inchangé tant qu'on ne recharge pas
    service.recharger_stats()
    assert service.snapshot_stats() == "2026-10-20_090000"
    assert len(service.get_stat("kpi")) == 4


def test_snapshot_actif_prioritaire_sur_le_plus_recent():
    d = depot()
    d.actif = "2026-10-08_100000"
    service = AppService(repository=d)
    assert service.snapshot_stats() == "2026-10-08_100000"
    assert len(service.get_stat("kpi")) == 1


def test_recharger_stats_suit_le_snapshot_actif():
    d = depot()
    d.actif = "2026-10-08_100000"
    service = AppService(repository=d)
    assert service.snapshot_stats() == "2026-10-08_100000"
    d.actif = "2026-10-12_132605"
    assert service.snapshot_stats() == "2026-10-08_100000"      # inchangé tant qu'on ne recharge pas
    service.recharger_stats()
    assert service.snapshot_stats() == "2026-10-12_132605"
