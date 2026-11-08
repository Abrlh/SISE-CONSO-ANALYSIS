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
from src.processing.preprocessing import ColonnesManquantesError
from src.orchestration.service import AppService
from tests.depot_actif import DepotActif


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
    from src.processing.preprocessing import verifier_colonnes_obligatoires
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


ANCIEN, NOUVEAU = "2026-10-08_100000", "2026-10-12_132605"


def test_service_lit_les_modeles_du_snapshot_actif(modele, tmp_path):
    m, X = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "59", ANCIEN, m, {"cible": "x", "colonnes": ["a"]})
    registre.save("classification", "59", NOUVEAU, m, {"cible": "y", "colonnes": ["a"]})   # entraînement en cours
    registre.save("classification", "75", NOUVEAU, m, {"cible": "y", "colonnes": ["a"]})
    depot = DepotActif(ANCIEN)
    service = AppService(repository=depot, registry=registre)
    assert service.info_modele("classification", "59")["snapshot_id"] == ANCIEN
    assert (service.predire("classification", "59", X) == m.predict(X)).all()
    with pytest.raises(FileNotFoundError, match=r"\['59'\]"):              # 75 n'existe que dans le nouveau
        service.info_modele("classification", "75")
    formulaire = service.formulaire()
    assert formulaire["snapshot"] == ANCIEN and list(formulaire["classification"]) == ["59"]
    assert depot.lus == [ANCIEN]


def test_service_garde_ses_modeles_si_le_snapshot_actif_change(modele, tmp_path):
    m, _ = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "59", ANCIEN, m, {})
    registre.save("classification", "59", NOUVEAU, m, {})
    depot = DepotActif(ANCIEN)
    service = AppService(repository=depot, registry=registre)
    depot.modeles = NOUVEAU
    assert service.info_modele("classification", "59")["snapshot_id"] == ANCIEN
    assert AppService(repository=depot, registry=registre).info_modele("classification", "59")["snapshot_id"] == NOUVEAU


def test_formulaire_lit_les_donnees_du_snapshot_source(modele, tmp_path):
    m, _ = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "59", NOUVEAU, m, {"snapshot_source": ANCIEN, "cible": "x", "colonnes": ["a"]})
    depot = DepotActif(ANCIEN, modeles=NOUVEAU)
    formulaire = AppService(repository=depot, registry=registre).formulaire()
    assert depot.lus == [ANCIEN] and formulaire["snapshot"] == ANCIEN


def test_service_sans_snapshot_actif_lit_le_plus_recent(modele, tmp_path):
    m, _ = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "59", ANCIEN, m, {})
    registre.save("classification", "59", NOUVEAU, m, {})
    service = AppService(repository=DepotActif(None), registry=registre)
    assert service.info_modele("classification", "59")["snapshot_id"] == NOUVEAU


def test_service_predire_et_departement_inconnu(modele, tmp_path):
    m, X = modele
    registre = ModelRegistry(root=tmp_path)
    registre.save("classification", "75", "2026-10-12_132605", m, {})
    service = AppService(repository=DepotActif(None), registry=registre)
    assert (service.predire("classification", "75", X) == m.predict(X)).all()
    with pytest.raises(FileNotFoundError, match=r"\['75'\]"):
        service.predire("classification", "69", X)


# Données de performance pour le front

def test_tableaux_evaluation_classification(modele):
    m, X = modele
    y = donnees()["etiquette_dpe"]
    t = m.tableaux_evaluation(X, y, y)
    assert set(t) == {"scores", "matrice_confusion", "par_etiquette", "importance_variables"}
    scores = t["scores"].set_index("metrique")
    assert list(scores.index) == ["f1_macro", "accuracy", "a_une_classe_pres"]
    # référence naïve : toujours l'étiquette la plus fréquente
    assert scores.loc["accuracy", "reference_naive"] == pytest.approx(y.value_counts(normalize=True).max())
    matrice = t["matrice_confusion"]
    assert list(matrice.columns) == ["vraie", "predite", "effectif", "pourcentage"]
    assert matrice["effectif"].sum() == len(y)
    assert matrice.groupby("vraie")["pourcentage"].sum().round().eq(100).all()
    assert list(t["par_etiquette"]["etiquette"]) == ["C", "D", "E"]
    assert set(t["importance_variables"]["variable"]) == set(VARIABLES_FORMULAIRE)


def test_tableaux_evaluation_regression():
    X, y = preparer_xy(donnees(), "conso_5_usages_par_m2_ef")
    m = RegressionModel()
    m.train(X, y)
    t = m.tableaux_evaluation(X, y, y)
    assert set(t) == {"scores", "predit_reel", "erreur_par_tranche", "importance_variables"}
    scores = t["scores"].set_index("metrique")
    assert scores.loc["mae", "unite"] == "kWh/m²/an"
    assert scores.loc["mae", "valeur"] < scores.loc["mae", "reference_naive"]   # mieux que la médiane
    assert list(t["predit_reel"].columns) == ["reel", "predit"]
    tranches = t["erreur_par_tranche"]
    assert tranches["effectif"].sum() == len(y)
    assert tranches["tranche"].iloc[-1] == "400 et plus"
    # la surface explique la cible : c'est la variable la plus importante
    assert t["importance_variables"]["variable"].iloc[0] == "surface_habitable_logement"


def test_evaluation_enregistree_et_relue_par_le_service(modele, tmp_path):
    m, X = modele
    y = donnees()["etiquette_dpe"]
    registre = ModelRegistry(root=tmp_path)
    tableaux = m.tableaux_evaluation(X, y, y)
    registre.save("classification", "75", "2026-10-12_132605", m, {}, tableaux)
    assert registre.load_meta("classification", "75")["evaluation"] == list(tableaux)
    service = AppService(repository=DepotActif(None), registry=registre)
    assert service.liste_evaluation("classification", "75") == list(tableaux)
    pd.testing.assert_frame_equal(service.evaluation_modele("classification", "75", "matrice_confusion"),
                                  tableaux["matrice_confusion"])
    with pytest.raises(KeyError, match="Disponibles"):
        service.evaluation_modele("classification", "75", "inconnu")
