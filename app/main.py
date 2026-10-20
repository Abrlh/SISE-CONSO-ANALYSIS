"""Point d'entrée de l'application Streamlit.

Lancement, depuis la racine du dépôt :

    streamlit run app/main.py

Ce fichier configure la page, déclare les pages de l'application et affiche le menu.
Chaque page est un script dans app/pages/ ; toutes utilisent le même AppService (voir app/deps.py).
"""

import sys
from pathlib import Path

# Ajoute la racine du dépôt au chemin d'import pour pouvoir écrire "from src.service import AppService"
RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import streamlit as st

# Doit être le premier appel Streamlit du script
st.set_page_config(
    page_title="CONSO.PROJET_SISE",
    page_icon=":material/bolt:",
    layout="wide",
)

# Le chemin de chaque page est relatif à ce fichier
pages = [
    st.Page("pages/data.py", title="Contexte", icon=":material/dataset:", default=True),
    st.Page("pages/stats.py", title="Visualisations", icon=":material/bar_chart:"),
    st.Page("pages/carte.py", title="Carte", icon=":material/map:"),
    st.Page("pages/prediction.py", title="Prédiction", icon=":material/online_prediction:"),
]

# Affiche le menu de navigation et exécute la page choisie
st.navigation(pages).run()
