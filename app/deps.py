"""Accès unique au back pour les pages Streamlit.

AppService est créé une seule fois (@st.cache_resource) et partagé
entre tous les utilisateurs : n'y stocker aucune donnée propre à un
utilisateur (utiliser st.session_state).
"""

import streamlit as st

from src.orchestration.service import AppService


@st.cache_resource
def get_service() -> AppService:
    """Renvoie l'instance unique d'AppService, créée au premier appel."""
    return AppService()
