"""
Tests unitaires de l'audit des colonnes (src/audit_colonnes.py). Données factices : aucun fichier lu.

Lancer : python -m pytest tests/test_audit.py -v
"""
import pandas as pd

from src.audit_colonnes import auditer, colonnes_utilisees


def brut():
    """Données brutes factices contenant toutes les colonnes utilisées par le code."""
    return pd.DataFrame({c: ["x"] * 20 for c in colonnes_utilisees()})


def test_toutes_les_colonnes_utilisees_presentes():
    manquantes, _, _ = auditer(brut())
    assert manquantes == {}


def test_colonne_utilisee_absente_signalee_avec_son_usage():
    manquantes, _, _ = auditer(brut().drop(columns=["type_energie_n1", "numero_dpe"]))
    assert manquantes["type_energie_n1"] == ["formulaire"]
    assert "nettoyage" in manquantes["numero_dpe"]


def test_cible_de_la_regression_surveillee():
    manquantes, _, _ = auditer(brut().drop(columns="conso_5_usages_par_m2_ef"))
    assert manquantes == {"conso_5_usages_par_m2_ef": ["cible"]}


def test_colonne_creee_par_le_nettoyage_remplacee_par_sa_source():
    # latitude / longitude viennent de _geopoint ; origine est ajoutée à la fusion
    utilisees = colonnes_utilisees()
    assert "_geopoint" in utilisees
    assert not {"latitude", "longitude", "origine"} & set(utilisees)


def test_nouvelles_et_disparues_par_rapport_au_snapshot_precedent():
    df = brut().rename(columns={"type_energie_n1": "type_energie_principale_n1"})
    _, nouvelles, disparues = auditer(df, colonnes_precedentes=brut().columns)
    assert list(nouvelles["colonne"]) == ["type_energie_principale_n1"]
    assert disparues == ["type_energie_n1"]


def test_sans_snapshot_precedent_pas_de_comparaison():
    _, nouvelles, disparues = auditer(brut().assign(autre=1))
    assert len(nouvelles) == 0 and disparues == []
