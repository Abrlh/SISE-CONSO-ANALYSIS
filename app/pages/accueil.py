"""Page « Accueil » : présente le projet et renvoie vers les autres pages."""

import streamlit as st

from affichage import ILLUSTRATION_SVG

gauche, droite = st.columns([3, 2])

with gauche:
    st.caption("GREENTECH SOLUTIONS POUR ENEDIS")
    st.title("Comprendre et prédire la performance énergétique des logements")
    st.write(
        "Cette application explore les diagnostics de performance énergétique (DPE) publiés par l'ADEME "
        "pour les logements existants et neufs. Elle permet de comparer les consommations selon "
        "l'étiquette (de A, très performant, à G, très énergivore), la surface ou le département, "
        "puis d'estimer l'étiquette et la consommation d'un logement à partir de ses caractéristiques."
    )

with droite:
    st.markdown(ILLUSTRATION_SVG, unsafe_allow_html=True)

st.subheader("Que souhaitez-vous faire ?")
colonnes = st.columns(3)

with colonnes[0]:
    with st.container(border=True):
        st.markdown("**Contexte**")
        st.write("Découvrir le jeu de données, la carte des logements, filtrer et rafraîchir les données.")
        st.page_link("pages/contexte.py", label="Ouvrir le contexte", icon=":material/dataset:")

with colonnes[1]:
    with st.container(border=True):
        st.markdown("**Statistiques**")
        st.write("Indicateurs clés et graphiques pour comparer la consommation par étiquette, surface et département.")
        st.page_link("pages/statistiques.py", label="Ouvrir les statistiques", icon=":material/bar_chart:")

with colonnes[2]:
    with st.container(border=True):
        st.markdown("**Prédiction**")
        st.write("Saisir les caractéristiques d'un logement pour estimer son étiquette et sa consommation.")
        st.page_link("pages/prediction.py", label="Ouvrir la prédiction", icon=":material/online_prediction:")

st.caption("Source des données : ADEME, DPE des logements existants et neufs. " \
"Projet M2 SISE Présenté par: Clara FONTAINE Aissatou Lamarana BARRY Nicole NGEJEJE.")
