"""
Tests unitaires de l'enregistrement des modèles (src/models/registry.py), du modèle de classification
et des prédictions du service. Petites données factices, dossier temporaire : models/ n'est pas touché.

Lancer : python -m pytest tests/test_registry.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.models.classification import ClassificationModel
from src.models.features import preparer_xy
from src.models.registry import ModelRegistry
from src.service import AppService


def donnees(n=120):
    rng = np.random.default_rng(0)
    surface = rng.uniform(20, 150, n)
    return pd.DataFrame({
        "surface_habitable_logement": surface,
        "type_batiment": rng.choice(["maison", "appartement"], n),
        "numero_dpe": [f"id{i}" for i in range(n)],                # identifiant : doit être retiré
        "conso_5_usages_par_m2_ep": surface * 2,                    # fuite : doit être retirée
        "etiquette_dpe": np.where(surface < 60, "C", np.where(surface < 100, "D", "E")),
    })


@pytest.fixture(scope="module")
def modele():
    X, y = preparer_xy(donnees(), "etiquette_dpe")
    m = ClassificationModel()
    m.train(X, y)
    return m, X


def test_preparer_xy_retire_cible_fuites_et_identifiants():
    X, y = preparer_xy(donnees(), "etiquette_dpe")
    assert list(X.columns) == ["surface_habitable_logement", "type_batiment"]
    assert y.name == "etiquette_dpe"


def test_train_choisit_k(modele):
    m, _ = modele
    assert m.meilleurs_params["selection__k"] in ClassificationModel.GRILLE_K


def test_modele_recharge_predit_pareil(modele, tmp_path):
    m, X = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "75", "2026-10-12_132605", m, {"colonnes": list(X.columns)})
    recharge = registre.load("classification", "75")
    assert (recharge.predict(X) == m.predict(X)).all()
    meta = registre.load_meta("classification", "75")
    assert meta["colonnes"] == list(X.columns)
    assert meta["departement"] == "75"


def test_load_prend_le_plus_recent_et_ignore_les_incomplets(modele, tmp_path):
    m, _ = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "59", "2026-10-08_100000", m, {})
    registre.save("classification", "59", "2026-10-12_132605", m, {})
    # enregistrement interrompu : pas de meta.json
    (tmp_path / "2026-10-20_000000" / "classification" / "59").mkdir(parents=True)
    assert registre.list_snapshots("classification", "59") == ["2026-10-08_100000", "2026-10-12_132605"]
    assert registre.load_meta("classification", "59")["snapshot_id"] == "2026-10-12_132605"


def test_load_sans_modele_leve_une_erreur(tmp_path):
    with pytest.raises(FileNotFoundError):
        ModelRegistry(root=tmp_path).load("classification", "75")


def test_service_predire_et_departement_inconnu(modele, tmp_path):
    m, X = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "75", "2026-10-12_132605", m, {})
    service = AppService(repository=object(), registry=registre)
    assert (service.predire("classification", "75", X) == m.predict(X)).all()
    with pytest.raises(FileNotFoundError, match=r"\['75'\]"):
        service.predire("classification", "69", X)
