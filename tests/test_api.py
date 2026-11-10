from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_sante():
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "ok"}


def test_departements_liste_les_deux_taches():
    reponse = client.get("/departements")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["classification"]
    assert corps["regression"]


def test_modele_tache_inconnue():
    assert client.get("/modeles/inconnue/59").status_code == 404


def test_modele_departement_inconnu():
    assert client.get("/modeles/regression/00").status_code == 404


def test_predict_colonnes_manquantes():
    departement = client.get("/departements").json()["regression"][0]
    reponse = client.post("/predict", json={"departement": departement, "caracteristiques": {}})
    assert reponse.status_code == 422
    assert reponse.json()["detail"]["colonnes"]