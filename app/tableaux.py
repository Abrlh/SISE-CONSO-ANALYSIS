"""Lecture des statistiques pré-calculées pour les pages.

L'interface ne lit jamais les fichiers parquet elle-même : elle demande les tableaux au service
(AppService.get_stat, via get_service de deps.py). Rien n'est recalculé ici.
"""

import streamlit as st
from deps import get_service


# cache_resource garde le tableau en mémoire sans le recopier à chaque page.
# Les pages ne doivent donc pas modifier un tableau lu : elles le filtrent (ce qui crée un nouveau tableau).
@st.cache_resource(show_spinner="Lecture des statistiques...")
def lire(nom):
    """Lit une statistique pré-calculée (un DataFrame pandas)."""
    return get_service().get_stat(nom)


def lire_ou_arreter(nom):
    """Lit un tableau, ou affiche un message clair et arrête la page si la lecture échoue."""
    try:
        return lire(nom)
    except FileNotFoundError as erreur:
        st.error(f"Statistiques introuvables : {erreur}")
        st.stop()
    except Exception as erreur:  # tableau absent, fichier illisible...
        st.error(f"Impossible de lire le tableau « {nom} » : {erreur}")
        st.stop()
