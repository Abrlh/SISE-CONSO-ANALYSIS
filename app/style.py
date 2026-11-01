"""Style de l'application : une couleur douce pour la page sélectionnée dans le menu.

Chaque page a sa couleur, choisie dans le thème de l'énergie. Le style est du CSS (la langue des
couleurs et des mises en forme du web), envoyé à Streamlit sous forme de texte. Aucun calcul ici.
"""

import streamlit as st

# Couleurs douces par page : (fond, trait à gauche, texte)
COULEURS_PAGES = {
    "Accueil": ("#DCEFD9", "#4CAF7A", "#1F5F3A"),       # vert : énergie verte
    "Contexte": ("#DCEBFA", "#3B82C4", "#1E4E79"),      # bleu : électricité, eau
    "Statistiques": ("#FFF1C9", "#F2B01E", "#7A5600"),  # jaune : lumière, électricité
    "Prédiction": ("#FFE3D1", "#F07F3C", "#8A3F10"),    # orange : chaleur, chauffage
}


def colorer_menu(titre_page):
    """Colore le lien de la page sélectionnée dans le menu de gauche."""
    if titre_page not in COULEURS_PAGES:
        return
    fond, trait, texte = COULEURS_PAGES[titre_page]
    # Dans le CSS, les accolades doivent être doublées quand le texte est un f-string
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebarNavLink"][aria-current="page"] {{
            background-color: {fond};
            border-left: 4px solid {trait};
        }}
        [data-testid="stSidebarNavLink"][aria-current="page"] * {{
            color: {texte};
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )