"""Page « Accueil » : présente le projet et renvoie vers les autres pages."""

import streamlit as st

from style import banniere_accueil, habiller_cartes

banniere_accueil()
habiller_cartes()

st.markdown('<div style="height: 1.5rem"></div>', unsafe_allow_html=True)
st.subheader(":material/explore: Que souhaitez-vous faire ?")
st.caption("Un parcours en trois étapes")
colonnes = st.columns(3)

# Le nom (key) de chaque carte sert à la colorer dans style.py : il doit commencer par « carte_ »
with colonnes[0]:
    with st.container(key="carte_contexte"):
        st.markdown("**:material/dataset: Contexte**")
        st.write("Découvrir le jeu de données, la carte des logements, filtrer et rafraîchir les données.")
        st.page_link("pages/contexte.py", label="Ouvrir le contexte", icon=":material/dataset:")

with colonnes[1]:
    with st.container(key="carte_statistiques"):
        st.markdown("**:material/bar_chart: Statistiques**")
        st.write("Indicateurs clés et graphiques pour comparer la consommation par étiquette, surface et département.")
        st.page_link("pages/statistiques.py", label="Ouvrir les statistiques", icon=":material/bar_chart:")

with colonnes[2]:
    with st.container(key="carte_prediction"):
        st.markdown("**:material/online_prediction: Prédiction**")
        st.write("Saisir les caractéristiques d'un logement pour estimer son étiquette et sa consommation.")
        st.page_link("pages/prediction.py", label="Ouvrir la prédiction", icon=":material/online_prediction:")
