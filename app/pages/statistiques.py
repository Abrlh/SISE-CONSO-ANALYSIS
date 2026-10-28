"""Page « Statistiques » : emplacements des indicateurs et des graphiques.

Rien n'est calculé ici. Chaque emplacement sera rempli avec les résultats préparés par le back end.
"""

import streamlit as st

from affichage import a_venir, widgets_filtres
from lecture import charger_ou_arreter

st.title("Statistiques")

donnees, meta = charger_ou_arreter()

# ---- Filtres (affichés, pas encore actifs)
st.sidebar.header("Filtres")
widgets_filtres(st.sidebar, [str(d) for d in meta.get("departements", [])], sorted(donnees["origine"].dropna().unique()))
st.sidebar.caption("Les filtres seront actifs quand les résultats du back end seront branchés.")

# ---- Exports (branchés plus tard)
colonnes_export = st.columns(2)
colonnes_export[0].button("Exporter les données filtrées (CSV)", icon=":material/download:", disabled=True)
colonnes_export[1].button("Exporter un graphique (PNG)", icon=":material/image:", disabled=True)

# ---- Chiffres clés
st.subheader("Chiffres clés")
noms_kpi = ["Nombre de DPE", "Conso moyenne", "Part de F et G", "Étiquette dominante", "Écart G vs A"]
for colonne, nom in zip(st.columns(len(noms_kpi)), noms_kpi):
    colonne.metric(nom, "à venir")

# ---- Graphiques par onglet
onglets = st.tabs(["Vue d'ensemble", "Consommation", "Facteurs", "Coût et GES", "Dans le temps"])

with onglets[0]:
    a_venir("Répartition des étiquettes DPE")
with onglets[1]:
    a_venir("Distribution de la consommation")
    a_venir("Consommation par étiquette")
with onglets[2]:
    a_venir("Effet des caractéristiques du logement (énergie, période, surface, isolation)")
with onglets[3]:
    a_venir("Coût et émissions de gaz à effet de serre")
with onglets[4]:
    a_venir("Évolution dans le temps")
