"""
Tests unitaires du nettoyage des anciens snapshots (TrainingPipeline.run).
Dossiers factices dans un dossier temporaire : data/ et models/ ne sont pas touchés.

Lancer : python -m pytest tests/test_nettoyage_snapshots.py -v
"""
import json

import pytest

from src.data.repository import DataRepository
from src.models.registry import ModelRegistry
from src.orchestration import train as module_train

S1, S2, S3, S4 = (f"2026-01-0{i}_000000" for i in range(1, 5))
DEPARTEMENTS = ("59", "69", "75")
TACHES = ("classification", "regression")


def fichier_meta(dossier):
    dossier.mkdir(parents=True)
    (dossier / "meta.json").write_text("{}")


@pytest.fixture
def racine(tmp_path):
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "stats").mkdir()
    (tmp_path / "data" / "processed").mkdir()
    (tmp_path / "models").mkdir()
    lignes = ["code,nb_lignes"] + [f"{d},1" for d in DEPARTEMENTS]
    (tmp_path / "data" / "raw" / "codes_departements_nb_lignes.csv").write_text("\n".join(lignes))
    return tmp_path


@pytest.fixture
def pipeline(racine, monkeypatch):
    monkeypatch.setattr(module_train, "DataRepository", lambda: DataRepository(root=racine / "data" / "raw"))
    monkeypatch.setattr(module_train, "ModelRegistry", lambda: ModelRegistry(root=racine / "models"))
    p = module_train.TrainingPipeline()
    monkeypatch.setattr(p, "train", lambda *args: None)  # seul le nettoyage est testé
    return p


def creer(racine, snapid, stats=True, modeles=DEPARTEMENTS):
    for dossier in ("raw", "processed"):
        fichier_meta(racine / "data" / dossier / snapid)
    if stats:
        fichier_meta(racine / "data" / "stats" / snapid)
    for tache in TACHES:
        for departement in modeles:
            fichier_meta(racine / "models" / snapid / tache / departement)


def present(racine, snapid):
    """Dossiers dans lesquels le snapshot existe encore."""
    dossiers = [racine / "data" / d for d in ("raw", "processed", "stats")] + [racine / "models"]
    return [d.name for d in dossiers if (d / snapid).exists()]


TOUS = ["raw", "processed", "stats", "models"]


def test_garde_les_deux_plus_recents_dans_les_quatre_dossiers(racine, pipeline):
    for s in (S1, S2, S3):
        creer(racine, s)
    pipeline.run(steps=["train"], snapid=S3)
    assert present(racine, S1) == []
    assert present(racine, S2) == TOUS
    assert present(racine, S3) == TOUS


def test_snapshot_interrompu_supprime(racine, pipeline):
    creer(racine, S1)
    (racine / "data" / "raw" / S2 / "59").mkdir(parents=True)  # téléchargement interrompu, sans meta.json
    creer(racine, S3)
    pipeline.run(steps=["train"], snapid=S3)
    assert present(racine, S2) == []
    assert present(racine, S1) == TOUS
    assert present(racine, S3) == TOUS


def test_modeles_partiels_non_comptes_comme_aboutis(racine, pipeline):
    for s in (S1, S2):
        creer(racine, s)
    creer(racine, S3, modeles=("59",))
    creer(racine, S4)
    pipeline.run(steps=["train"], snapid=S4)
    assert present(racine, S1) == []
    assert present(racine, S2) == TOUS
    assert present(racine, S3) == []
    assert present(racine, S4) == TOUS


def test_stats_absentes_non_comptees_comme_abouties(racine, pipeline):
    for s in (S1, S2):
        creer(racine, s)
    creer(racine, S3, stats=False)
    pipeline.run(steps=["train"], snapid=S3)
    assert present(racine, S1) == TOUS
    assert present(racine, S2) == TOUS
    assert present(racine, S3) == ["raw", "processed", "models"]  # plus récent : en attente


def test_snapshot_recent_en_attente_conserve(racine, pipeline):
    for s in (S1, S2):
        creer(racine, s)
    fichier_meta(racine / "data" / "raw" / S3)  # téléchargé, pas encore entraîné
    pipeline.run(steps=["train"], snapid=S2)
    assert present(racine, S3) == ["raw"]


def test_fichiers_et_autres_dossiers_conserves(racine, pipeline):
    (racine / "data" / "raw" / ".ipynb_checkpoints").mkdir()
    for s in (S1, S2, S3):
        creer(racine, s)
    pipeline.run(steps=["train"], snapid=S3)
    assert (racine / "data" / "raw" / "codes_departements_nb_lignes.csv").exists()
    assert (racine / "data" / "raw" / ".ipynb_checkpoints").exists()


def test_aucun_nettoyage_sans_etape_train(racine, pipeline):
    for s in (S1, S2, S3):
        creer(racine, s)
    pipeline.run(steps=[], snapid=S3)
    assert present(racine, S1) == TOUS


def actif(racine):
    return DataRepository(root=racine / "data" / "raw").snapshot_actif()


def test_snapshot_actif_absent_au_depart(racine):
    assert actif(racine) is None


def test_entrainement_publie_le_dernier_snapshot_abouti(racine, pipeline):
    for s in (S1, S2, S3):
        creer(racine, s)
    pipeline.run(steps=["train"], snapid=S3)
    assert actif(racine) == S3
    assert not (racine / "data" / "snapshot_actif.tmp").exists()


def test_snapshot_non_abouti_non_publie(racine, pipeline):
    creer(racine, S1)
    pipeline.run(steps=["train"], snapid=S1)
    creer(racine, S2, stats=False)
    pipeline.run(steps=["train"], snapid=S2)
    assert actif(racine) == S1


def test_modeles_partiels_non_publies(racine, pipeline):
    creer(racine, S1)
    creer(racine, S2, modeles=("59",))
    pipeline.run(steps=["train"], snapid=S2)
    assert actif(racine) == S1


def test_pas_de_publication_sans_etape_train(racine, pipeline):
    creer(racine, S1)
    pipeline.run(steps=[], snapid=S1)
    assert actif(racine) is None


def depot(racine):
    return DataRepository(root=racine / "data" / "raw")


def creer_version(racine, version, source):
    for tache in TACHES:
        for departement in DEPARTEMENTS:
            dossier = racine / "models" / version / tache / departement
            dossier.mkdir(parents=True)
            (dossier / "meta.json").write_text(json.dumps({"snapshot_source": source}))


def entrainement_factice(racine, vus):
    """Remplace TrainingPipeline.train : note la version écrite et celle affichée pendant l'entraînement, puis écrit les modèles."""
    def train(snapid, processed, version):
        vus.append((version, depot(racine).modeles_actifs()))
        creer_version(racine, version, snapid)
    return train


DONNEES = ["raw", "processed", "stats"]


def test_reentrainement_cree_une_version_de_modeles_sans_copier_les_donnees(racine, pipeline, monkeypatch):
    creer(racine, S1)
    depot(racine).definir_snapshot_actif(S1, S1)
    vus = []
    monkeypatch.setattr(pipeline, "train", entrainement_factice(racine, vus))
    pipeline.run(steps=["train"], snapid=S1)
    version, affichee_pendant = vus[0]
    assert version != S1 and affichee_pendant == S1     # l'application lit les anciens modèles pendant l'entraînement
    assert actif(racine) == S1 and depot(racine).modeles_actifs() == version
    assert present(racine, S1) == TOUS
    assert present(racine, version) == ["models"]       # aucune donnée recopiée


def test_sans_pointeur_les_modeles_affiches_sont_quand_meme_proteges(racine, pipeline, monkeypatch):
    creer(racine, S1)
    vus = []
    monkeypatch.setattr(pipeline, "train", entrainement_factice(racine, vus))
    pipeline.run(steps=["train"], snapid=S1)
    assert vus[0][0] != S1 and vus[0][1] == S1


def test_echec_du_reentrainement_laisse_les_anciens_modeles_actifs(racine, pipeline, monkeypatch):
    creer(racine, S1)
    depot(racine).definir_snapshot_actif(S1, S1)

    def echec(snapid, processed, version):
        raise RuntimeError("entraînement impossible")

    monkeypatch.setattr(pipeline, "train", echec)
    with pytest.raises(RuntimeError):
        pipeline.run(steps=["train"], snapid=S1)
    assert depot(racine).modeles_actifs() == S1
    assert present(racine, S1) == TOUS


def test_snapshot_non_affiche_entraine_sur_place(racine, pipeline, monkeypatch):
    for s in (S1, S2):
        creer(racine, s)
    depot(racine).definir_snapshot_actif(S2, S2)
    vus = []
    monkeypatch.setattr(pipeline, "train", lambda snapid, processed, version: vus.append(version))
    pipeline.run(steps=["train"], snapid=S1)
    assert vus == [S1]
    assert actif(racine) == S2


def test_nettoyage_garde_deux_versions_et_leur_snapshot_source(racine, pipeline, monkeypatch):
    creer(racine, S1)
    creer_version(racine, S2, S1)
    creer_version(racine, S3, S1)
    depot(racine).definir_snapshot_actif(S1, S3)
    vus = []
    monkeypatch.setattr(pipeline, "train", entrainement_factice(racine, vus))
    pipeline.run(steps=["train"], snapid=S1)
    assert present(racine, S1) == DONNEES               # modèles d'origine supprimés, données conservées
    assert present(racine, S2) == []
    assert present(racine, S3) == ["models"]
    assert present(racine, vus[0][0]) == ["models"]


def test_reentrainements_gardent_le_telechargement_precedent(racine, pipeline, monkeypatch):
    for s in (S1, S2, S3):
        creer(racine, s)
    creer_version(racine, S4, S3)
    depot(racine).definir_snapshot_actif(S3, S4)
    vus = []
    monkeypatch.setattr(pipeline, "train", entrainement_factice(racine, vus))
    pipeline.run(steps=["train"], snapid=S3)
    assert present(racine, S1) == []                    # plus ancien que les deux derniers téléchargements
    assert present(racine, S2) == TOUS                  # téléchargement précédent : données et modèles
    assert present(racine, S3) == DONNEES
    assert present(racine, S4) == ["models"]            # version lue par l'application déjà lancée
    assert actif(racine) == S3 and depot(racine).modeles_actifs() == vus[0][0]


def test_aucun_snapshot_abouti_rien_supprime(racine, pipeline):
    creer(racine, S1, stats=False)
    creer(racine, S2, modeles=("59",))
    pipeline.run(steps=["train"], snapid=S2)
    assert present(racine, S1) == ["raw", "processed", "models"]
    assert present(racine, S2) == TOUS
