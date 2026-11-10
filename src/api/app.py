"""API REST des modèles : même moteur de prédiction que l'application Streamlit (via AppService)."""
from functools import lru_cache
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..data.repository import DataRepository
from ..models.registry import ModelRegistry
from ..orchestration.service import AppService

TACHES = ("classification", "regression")
# nom de la clé dans la réponse, pour chaque tâche
SORTIES = {"classification": "etiquette_dpe", "regression": "conso_kwh_m2_an"}

app = FastAPI(
    title="API DPE - GreenTech Solutions",
    description="Prédit l'étiquette DPE et la consommation (kWh/m²/an) d'un logement.",
)


@lru_cache(maxsize=1)
def _contexte() -> tuple[DataRepository, ModelRegistry, AppService]:
    """Crée une seule fois le service (les modèles chargés restent en cache)."""
    repository = DataRepository()
    registry = ModelRegistry()
    return repository, registry, AppService(repository, registry)


class DemandePrediction(BaseModel):
    departement: str = Field(..., examples=["59"], description="Numéro du département")
    caracteristiques: dict[str, Any] = Field(
        ..., description="Une valeur par colonne attendue (voir GET /modeles/{tache}/{departement})"
    )


@app.get("/sante")
def sante() -> dict:
    """Vérifie que l'API tourne."""
    return {"statut": "ok"}


@app.get("/departements")
def departements() -> dict:
    """Départements pour lesquels un modèle existe, par tâche."""
    repository, registry, _ = _contexte()
    modeles = repository.modeles_actifs()
    resultat = {"modeles": modeles}
    for tache in TACHES:
        resultat[tache] = registry.list_departements(tache, modeles)
    return resultat


@app.get("/modeles/{tache}/{departement}")
def modele(tache: str, departement: str) -> dict:
    """Informations du modèle : colonnes attendues, cible, métriques..."""
    if tache not in TACHES:
        raise HTTPException(404, f"Tâche inconnue : {tache}. Choix : {list(TACHES)}")
    _, _, service = _contexte()
    try:
        return service.info_modele(tache, departement)
    except FileNotFoundError as erreur:
        raise HTTPException(404, str(erreur))


@app.post("/predict")
def predict(demande: DemandePrediction) -> dict:
    """Prédit l'étiquette DPE (classification) et la consommation (régression)."""
    _, _, service = _contexte()
    resultat = {"departement": demande.departement}
    for tache in TACHES:
        try:
            colonnes = service.info_modele(tache, demande.departement)["colonnes"]
        except FileNotFoundError as erreur:
            raise HTTPException(404, str(erreur))

        absentes = [c for c in colonnes if c not in demande.caracteristiques]
        if absentes:
            raise HTTPException(422, {"message": f"Colonnes manquantes pour {tache}", "colonnes": absentes})

        X = pd.DataFrame([demande.caracteristiques])[colonnes]
        try:
            brut = service.predire(tache, demande.departement, X)[0]
        except (ValueError, TypeError, KeyError) as erreur:
            raise HTTPException(422, f"Valeurs invalides pour {tache} : {erreur}")
        resultat[SORTIES[tache]] = round(float(brut), 1) if tache == "regression" else str(brut)
    return resultat