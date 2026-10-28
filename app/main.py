"""Point d'entrée de l'application Streamlit.

Lancement, depuis la racine du dépôt :

    python -m streamlit run app/main.py

Ce fichier configure la page, déclare les pages de l'application et affiche le menu.
Chaque page est un script dans app/pages/. L'interface ne fait aucun calcul : elle lit et affiche.
"""

import streamlit as st

# Doit être le premier appel Streamlit du script
st.set_page_config(
    page_title="CONSO.PROJET_SISE",
    page_icon=":material/bolt:",
    layout="wide",
)

# Le chemin de chaque page est relatif à ce fichier
pages = [
    st.Page("pages/accueil.py", title="Accueil", icon=":material/home:", default=True),
    st.Page("pages/contexte.py", title="Contexte", icon=":material/dataset:"),
    st.Page("pages/statistiques.py", title="Statistiques", icon=":material/bar_chart:"),
    st.Page("pages/prediction.py", title="Prédiction", icon=":material/online_prediction:"),
]

# Affiche le menu de navigation et exécute la page choisie
st.navigation(pages).run()
