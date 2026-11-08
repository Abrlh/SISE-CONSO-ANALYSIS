"""Lecture des données nettoyées. Aucun calcul : les fichiers sont lus et rendus tels quels.

Les fichiers sont dans data/processed/<snapshot>/ : un fichier <département>.parquet par
département et un meta.json qui donne l'identifiant du snapshot et la liste des départements.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DOSSIER_PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
FICHIER_SNAPSHOT_ACTIF = DOSSIER_PROCESSED.parent / "snapshot_actif.json"

# Snapshot à lire. Mettre None pour lire automatiquement le snapshot actif (à défaut, le plus récent).
SNAPSHOT_CHOISI = None


def dernier_snapshot():
    """Chemin du dossier de snapshot à lire (SNAPSHOT_CHOISI, sinon le snapshot actif, sinon le plus récent), ou None s'il n'y en a pas."""
    if not DOSSIER_PROCESSED.exists():
        return None
    snapshot = SNAPSHOT_CHOISI
    if not snapshot and FICHIER_SNAPSHOT_ACTIF.exists():
        snapshot = json.loads(FICHIER_SNAPSHOT_ACTIF.read_text(encoding="utf-8"))["snapshot_id"]
    if snapshot:
        choisi = DOSSIER_PROCESSED / snapshot
        return choisi if choisi.is_dir() else None
    dossiers = sorted(d for d in DOSSIER_PROCESSED.iterdir() if d.is_dir())
    return dossiers[-1] if dossiers else None


# cache_resource garde le tableau en mémoire sans le recopier à chaque page (plus rapide que cache_data)
@st.cache_resource(show_spinner="Lecture des données...")
def lire_donnees():
    """Lit les fichiers parquet du dernier snapshot et renvoie (tableau, meta). Tableau vide si aucun fichier."""
    dossier = dernier_snapshot()
    if dossier is None:
        return pd.DataFrame(), {}
    meta_fichier = dossier / "meta.json"
    meta = json.loads(meta_fichier.read_text(encoding="utf-8")) if meta_fichier.exists() else {}
    morceaux = [pd.read_parquet(f) for f in sorted(dossier.glob("*.parquet"))]
    if not morceaux:
        return pd.DataFrame(), meta
    return pd.concat(morceaux, ignore_index=True), meta


def charger_ou_arreter():
    """Renvoie (tableau, meta) ou affiche un message clair et arrête la page si les données sont absentes."""
    try:
        donnees, meta = lire_donnees()
    except Exception as erreur:  # fichier illisible, pyarrow absent...
        st.error(f"Impossible de lire les données : {erreur}")
        st.stop()
    if donnees.empty:
        st.error("Aucune donnée nettoyée trouvée dans data/processed/. Récupérez les fichiers de la branche principale.")
        st.stop()
    return donnees, meta
