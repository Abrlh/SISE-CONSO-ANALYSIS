"""
Tests unitaires du choix du snapshot lu par l'application (app/lecture.py).
Dossier temporaire : data/ n'est pas touché.

Lancer : python -m pytest tests/test_lecture.py -v
"""
import json

import pytest

from app import lecture

ANCIEN, NOUVEAU = "2026-10-08_100000", "2026-10-12_132605"


@pytest.fixture
def processed(tmp_path, monkeypatch):
    dossier = tmp_path / "processed"
    (dossier / ANCIEN).mkdir(parents=True)
    (dossier / NOUVEAU).mkdir()
    monkeypatch.setattr(lecture, "DOSSIER_PROCESSED", dossier)
    monkeypatch.setattr(lecture, "FICHIER_SNAPSHOT_ACTIF", tmp_path / "snapshot_actif.json")
    monkeypatch.setattr(lecture, "SNAPSHOT_CHOISI", None)
    return dossier


def publier(snapshot):
    lecture.FICHIER_SNAPSHOT_ACTIF.write_text(json.dumps({"snapshot_id": snapshot}))


def test_sans_snapshot_actif_lit_le_plus_recent(processed):
    assert lecture.dernier_snapshot() == processed / NOUVEAU


def test_snapshot_actif_prioritaire_sur_le_plus_recent(processed):
    publier(ANCIEN)
    assert lecture.dernier_snapshot() == processed / ANCIEN


def test_snapshot_choisi_prioritaire_sur_le_snapshot_actif(processed, monkeypatch):
    publier(ANCIEN)
    monkeypatch.setattr(lecture, "SNAPSHOT_CHOISI", NOUVEAU)
    assert lecture.dernier_snapshot() == processed / NOUVEAU
