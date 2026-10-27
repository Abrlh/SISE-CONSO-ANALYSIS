"""
EXEMPLE minimal : afficher des statistiques pré-calculées dans une page Streamlit.

Ce fichier n'est PAS une page de l'application (il est dans docs/) : à copier dans
app/pages/ sous un nom comme 5_Mon_Test.py, puis à adapter.

À retenir :
1. On ne lit jamais les fichiers parquet directement : on passe par get_service().get_stat(nom).
2. Rien n'est recalculé. Chaque tableau contient déjà les sous-totaux "Tous" :
   un filtre, c'est seulement choisir des lignes.
3. La lecture est mise dans une fonction avec @st.cache_data pour ne pas relire à chaque clic.
4. La liste des tableaux et leurs colonnes : docs/analyse_statistiques.md.
"""
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

# Ajoute la racine du projet (page dans app/pages/) pour que "from app.deps import ..." marche
# (à adapter si main.py importe le service autrement)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.deps import get_service  # noqa: E402

st.set_page_config(page_title="Exemple", layout="wide")


@st.cache_data
def lire(nom):
    """Lit un tableau pré-calculé (un DataFrame pandas) ; gardé en mémoire ensuite."""
    return get_service().get_stat(nom)


st.title("Exemple : statistiques pré-calculées")

# 1. Un tableau de chiffres clés, filtré avec deux listes
kpi = lire("kpi_globaux")
dept = st.sidebar.selectbox("Département", ["Tous"] + sorted(d for d in kpi["departement"].unique() if d != "Tous"))
origine = st.sidebar.selectbox("Origine", ["Tous"] + sorted(o for o in kpi["origine"].unique() if o != "Tous"))

ligne = kpi[(kpi["departement"] == dept) & (kpi["origine"] == origine)].iloc[0]
col1, col2, col3 = st.columns(3)
col1.metric("Logements", f"{int(ligne['nb_logements']):,}".replace(",", " "))
col2.metric("Consommation médiane", f"{ligne['conso_mediane']:.0f} kWh/m²/an")
col3.metric("Passoires (F-G)", f"{ligne['part_f_g']:.1f} %")

# 2. Un graphique à partir d'un autre tableau, filtré de la même façon
etiquettes = lire("repartition_etiquettes")
etiquettes = etiquettes[(etiquettes["departement"] == dept) & (etiquettes["origine"] == origine)]
fig = px.bar(etiquettes, x="etiquette", y="pourcentage", title="Répartition des étiquettes DPE (%)")
st.plotly_chart(fig, use_container_width=True)   # l'icône appareil photo exporte en PNG

# 3. Voir tous les tableaux disponibles
with st.expander("Tableaux disponibles"):
    st.write(get_service().liste_stats())
