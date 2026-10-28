"""Page « Contexte » : présente le jeu de données, la carte, les filtres et le rafraîchissement.

Cette page ne calcule rien : elle lit les fichiers nettoyés et les affiche.
"""

import streamlit as st

from affichage import widgets_filtres
from lecture import charger_ou_arreter

st.title("Contexte")

donnees, meta = charger_ou_arreter()

# ---- Présentation du jeu de données
st.subheader("Présentation du jeu de données")
st.write(
    "Les diagnostics de performance énergétique (DPE) sont publiés par l'ADEME. Le jeu rassemble les logements "
    "existants et les logements neufs. Chaque ligne décrit un logement : sa surface, sa période de construction, "
    "son chauffage, la qualité de son isolation, sa consommation et son étiquette, de A (sobre) à G (énergivore)."
)
st.info("Les chiffres de synthèse (taille des données, valeurs retirées au nettoyage, cases vides) seront affichés ici.")

# ---- Carte et filtres
st.subheader("Explorer la carte")
with st.expander("Filtres", expanded=True):
    departements = [str(d) for d in meta.get("departements", [])]
    origines = sorted(donnees["origine"].dropna().unique())
    widgets_filtres(st, departements, origines)
    st.caption("Les filtres seront actifs quand les résultats du back end seront branchés.")

# La carte lit les coordonnées déjà présentes dans les fichiers
# Pour que la page reste rapide, la carte affiche au plus NB_POINTS_CARTE logements pris au hasard
NB_POINTS_CARTE = 5000
if {"latitude", "longitude"} <= set(donnees.columns):
    points = donnees[["latitude", "longitude"]].dropna()
    # Ne garde que les points situés en France métropolitaine : un point isolé très loin dézoomerait toute la carte
    points = points[points["latitude"].between(41.0, 51.5) & points["longitude"].between(-5.5, 10.0)]
    if len(points) > NB_POINTS_CARTE:
        points = points.sample(NB_POINTS_CARTE, random_state=0)
    st.map(points, latitude="latitude", longitude="longitude", size=40)
    st.caption(f"{len(points):,} logements affichés sur la carte (sélection au hasard).".replace(",", " "))
else:
    st.warning("Les colonnes latitude et longitude sont absentes de ces données : la carte ne peut pas s'afficher.")

# ---- Rafraîchissement des données
st.subheader("Rafraîchir les données")
with st.expander("Télécharger un nouveau snapshot depuis l'API ADEME"):
    st.write(
        "Cette action téléchargera à nouveau les DPE de chaque département depuis l'API de l'ADEME. "
        "Elle sera branchée sur le back end plus tard."
    )
    st.checkbox("Je confirme le téléchargement")
    st.button("Rafraîchir les données", disabled=True)

# ---- Aperçu
st.subheader("Aperçu des données")
st.dataframe(donnees.head(20))