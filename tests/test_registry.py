"""
Tests unitaires de l'enregistrement des modèles (src/models/registry.py), du modèle de classification
et des prédictions du service. Petites données factices, dossier temporaire : models/ n'est pas touché.

Lancer : python -m pytest tests/test_registry.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.models.classification import ClassificationModel
from src.models.features import VARIABLES_FORMULAIRE, preparer_xy
from src.models.regression import RegressionModel
from src.models.registry import ModelRegistry
from src.preprocessing import ColonnesManquantesError
from src.service import AppService


def donnees(n=120):
    rng = np.random.default_rng(0)
    surface = rng.uniform(20, 150, n)
    # variables du formulaire : valeurs quelconques, seule la surface explique l'étiquette
    df = pd.DataFrame({v: rng.choice(["a", "b"], n) for v in VARIABLES_FORMULAIRE})
    df["surface_habitable_logement"] = surface
    df["annee_construction"] = rng.integers(1900, 2020, n).astype(float)
    return df.assign(
        numero_dpe=[f"id{i}" for i in range(n)],                    # identifiant : exclu
        conso_5_usages_par_m2_ep=surface * 2,                       # fuite : exclue
        conso_5_usages_par_m2_ef=300 - surface,                     # cible de la régression
        deperditions_murs=surface * 0.5,                            # calcul DPE : exclue
        etiquette_dpe=np.where(surface < 60, "C", np.where(surface < 100, "D", "E")),
    )


@pytest.fixture(scope="module")
def modele():
    X, y = preparer_xy(donnees(), "etiquette_dpe")
    m = ClassificationModel()
    m.train(X, y)
    return m, X


def test_preparer_xy_ne_garde_que_les_variables_du_formulaire():
    # cible, identifiant, fuite et variable de calcul exclues ; ordre de VARIABLES_FORMULAIRE
    X, y = preparer_xy(donnees(), "etiquette_dpe")
    assert list(X.columns) == VARIABLES_FORMULAIRE
    assert y.name == "etiquette_dpe"


def test_preparer_xy_bloque_si_une_variable_manque():
    # ex. l'API a renommé type_energie_n1 : l'entraînement doit s'arrêter, pas continuer sans
    df = donnees().rename(columns={"type_energie_n1": "type_energie_principale_n1"})
    with pytest.raises(ColonnesManquantesError) as erreur:
        preparer_xy(df, "etiquette_dpe")
    assert erreur.value.colonnes == ["type_energie_n1"]


def test_meme_erreur_au_nettoyage_et_aux_modeles():
    from src.preprocessing import verifier_colonnes_obligatoires
    with pytest.raises(ColonnesManquantesError) as erreur:
        verifier_colonnes_obligatoires(donnees().drop(columns="numero_dpe"))
    assert erreur.value.colonnes == ["numero_dpe"]


def test_regression_entraine_predit_et_evalue():
    X, y = preparer_xy(donnees(), "conso_5_usages_par_m2_ef")
    assert list(X.columns) == VARIABLES_FORMULAIRE      # mêmes variables que la classification
    m = RegressionModel()
    m.train(X, y)
    assert m.predict(X).shape == (len(X),)
    metriques = m.evaluate(X, y)
    assert set(metriques) == {"r2", "mae", "rmse"}
    assert metriques["r2"] > 0.5                        # la surface explique la cible
    assert m.meilleurs_params == {}                     # pas de recherche d'hyperparamètres


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
