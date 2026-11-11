"""
Tests unitaires du client du workflow de réentraînement (src/orchestration/workflow_github.py).
Les appels HTTP sont simulés : aucun workflow n'est lancé.

Lancer : python -m pytest tests/test_workflow_github.py -v
"""
from unittest.mock import MagicMock

import pytest

from src.orchestration import workflow_github as module
from src.orchestration.workflow_github import WorkflowGitHub, mot_de_passe_valide

URL = "https://api.github.com/repos/moi/depot/actions/workflows/retrain.yml"


@pytest.fixture
def http(monkeypatch):
    faux = MagicMock()
    monkeypatch.setattr(module, "requests", faux)
    return faux


@pytest.fixture
def variables(monkeypatch):
    monkeypatch.setenv("GITHUB_DEPOT", "moi/depot")
    monkeypatch.setenv("GITHUB_TOKEN", "jeton")
    monkeypatch.setenv("MOT_DE_PASSE_ADMIN", "sésame")
    monkeypatch.delenv("GITHUB_BRANCHE", raising=False)


def test_lancer_vise_la_branche_avec_le_token(http):
    WorkflowGitHub("moi/depot", "jeton", "Refresh").lancer()
    args = http.post.call_args
    assert args.args[0] == f"{URL}/dispatches"
    assert args.kwargs["json"] == {"ref": "Refresh"}
    assert args.kwargs["headers"]["Authorization"] == "Bearer jeton"
    http.post.return_value.raise_for_status.assert_called_once()


def test_lancer_avec_rafraichissement_transmet_l_entree_du_workflow(http):
    WorkflowGitHub("moi/depot", "jeton").lancer(rafraichir=True)
    assert http.post.call_args.kwargs["json"] == {"ref": "master", "inputs": {"rafraichir": "true"}}


def test_dernier_run_format_compatible_avec_les_versions(http):
    http.get.return_value.json.return_value = {"workflow_runs": [{
        "id": 7, "status": "in_progress", "conclusion": None, "html_url": "lien",
        "created_at": "2026-11-08T15:15:16Z",
    }]}
    run = WorkflowGitHub("moi/depot", "jeton").dernier_run()
    assert run == {"id": 7, "statut": "in_progress", "conclusion": None, "url": "lien", "cree_le": "2026-11-08_151516"}
    assert http.get.call_args.kwargs["params"]["branch"] == "master"


def test_dernier_run_absent(http):
    http.get.return_value.json.return_value = {"workflow_runs": []}
    assert WorkflowGitHub("moi/depot", "jeton").dernier_run() is None


def test_erreur_http_remontee(http):
    http.get.return_value.raise_for_status.side_effect = RuntimeError("401")
    with pytest.raises(RuntimeError):
        WorkflowGitHub("moi/depot", "jeton").dernier_run()


def test_depuis_environnement_complet(variables):
    assert isinstance(WorkflowGitHub.depuis_environnement(), WorkflowGitHub)


@pytest.mark.parametrize("variable", ["GITHUB_DEPOT", "GITHUB_TOKEN", "MOT_DE_PASSE_ADMIN"])
def test_depuis_environnement_incomplet(variables, monkeypatch, variable):
    monkeypatch.delenv(variable)
    assert WorkflowGitHub.depuis_environnement() is None


def test_mot_de_passe(variables):
    assert mot_de_passe_valide("sésame")
    assert not mot_de_passe_valide("faux")
    assert not mot_de_passe_valide("")


def test_mot_de_passe_refuse_si_non_configure(monkeypatch):
    monkeypatch.delenv("MOT_DE_PASSE_ADMIN", raising=False)
    assert not mot_de_passe_valide("")
