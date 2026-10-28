"""Accès unique au back pour les pages Streamlit.

Streamlit réexécute tout le script d'une page à chaque interaction (clic,
saisie, slider). Sans précaution, AppService serait recréé à chaque fois, ce
qui rechargerait les modèles et les données à chaque clic.

@st.cache_resource évite cela : la fonction décorée ne s'exécute qu'au premier
appel, puis Streamlit renvoie le même objet aux appels suivants.

Attention : cet objet est partagé entre tous les utilisateurs de l'application.
AppService ne doit donc contenir aucune donnée propre à un utilisateur
(utiliser st.session_state pour cela).

Utilisation dans une page :

    from deps import get_service

    service = get_service()
"""

import streamlit as st

from src.service import AppService


@st.cache_resource
def get_service() -> AppService:
    """Renvoie l'instance unique d'AppService, créée au premier appel."""
    return AppService()
