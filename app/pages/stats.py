"""Page « Visualisations » : filtres dynamiques et graphiques sur les logements sélectionnés.

Cette page ne calcule rien : elle envoie les filtres à AppService (service.get_visualisations)
et affiche les résultats. Les calculs sont dans StatAnalyzer.
"""

import altair as alt
import streamlit as st
from affichage import COULEURS_ETIQUETTES, fmt_nombre
from deps import get_service

from src.analysis import (
    COL_CONSO,
    COL_ETIQUETTE,
    COL_SURFACE,
    ETIQUETTES,
    NOMS_DEPARTEMENTS,
    UNITE_CONSO,
)

service = get_service()

st.title("Visualisations")

try:
    options = service.get_options_filtres()
except (FileNotFoundError, ValueError) as erreur:
    st.error(f"Impossible de charger les données : {erreur}")
    st.stop()

# ---- Filtres (barre latérale)
st.sidebar.header("Filtres")

departement = st.sidebar.selectbox(
    "Département",
    ["Tous"] + options["departements"],
    format_func=lambda code: code if code == "Tous" else f"{NOMS_DEPARTEMENTS.get(code, code)} ({code})",
)
origine = st.sidebar.radio("Origine du logement", ["Tous"] + options["origines"])
etiquettes = st.sidebar.multiselect("Étiquettes DPE", options["etiquettes"], default=options["etiquettes"])
if options["surface_min"] < options["surface_max"]:
    surface = st.sidebar.slider(
        "Surface habitable (m²)",
        options["surface_min"],
        options["surface_max"],
        (options["surface_min"], options["surface_max"]),
    )
else:
    surface = None
sans_extremes = st.sidebar.checkbox(
    "Masquer les consommations extrêmes",
    value=True,
    help="Retire le 1 % de logements les plus consommateurs pour rendre les graphiques lisibles.",
)

filtres = {
    "departements": None if departement == "Tous" else [departement],
    "origines": None if origine == "Tous" else [origine],
    "etiquettes": etiquettes,
    "surface": surface,
    "sans_extremes": sans_extremes,
}

resultats = service.get_visualisations(filtres)

st.caption(
    f"{fmt_nombre(resultats['nb_filtre'])} logements sur {fmt_nombre(resultats['nb_total'])} "
    "correspondent aux filtres choisis."
)
if resultats["nb_filtre"] == 0:
    st.warning("Aucun logement ne correspond à ces filtres : élargissez la sélection dans la barre latérale.")
    st.stop()

# ---- Indicateurs de la sélection
kpi = resultats["kpi"]
colonnes = st.columns(3)
colonnes[0].metric("Nombre de DPE", fmt_nombre(kpi["nb_dpe"]))
colonnes[1].metric(
    "Conso moyenne",
    fmt_nombre(kpi["conso_moyenne"]),
    help=f"Médiane : {fmt_nombre(kpi['conso_mediane'])} {UNITE_CONSO}.",
)
colonnes[2].metric(
    "Part de F et G",
    "n/a" if kpi["part_fg"] is None else f"{kpi['part_fg'] * 100:.1f} %",
)

# ---- Graphiques
onglet_conso, onglet_etiquettes, onglet_surface, onglet_departements = st.tabs(
    ["Consommation", "Étiquettes", "Surface et consommation", "Départements"]
)

with onglet_conso:
    st.subheader("Distribution de la consommation")
    st.caption(f"Nombre de logements par tranche de consommation ({UNITE_CONSO}).")
    st.bar_chart(resultats["histogramme"])

with onglet_etiquettes:
    gauche, droite = st.columns(2)
    with gauche:
        st.subheader("Répartition des étiquettes")
        st.bar_chart(resultats["repartition_etiquettes"])
    with droite:
        st.subheader("Consommation par étiquette")
        st.caption("Boîte : 50 % des logements (du 1er au 3e quartile). Trait blanc : médiane. Ligne : étendue hors valeurs extrêmes.")
        base = alt.Chart(resultats["boites"]).encode(
            x=alt.X("etiquette:N", sort=ETIQUETTES, title="Étiquette DPE"),
            color=alt.Color(
                "etiquette:N",
                scale=alt.Scale(domain=ETIQUETTES, range=COULEURS_ETIQUETTES),
                legend=None,
            ),
        )
        moustaches = base.mark_rule().encode(y=alt.Y("bas:Q", title=f"Consommation ({UNITE_CONSO})"), y2="haut:Q")
        boites = base.mark_bar(size=28).encode(y="q1:Q", y2="q3:Q")
        medianes = base.mark_tick(color="white", size=28, thickness=2).encode(y="mediane:Q")
        st.altair_chart(moustaches + boites + medianes)

with onglet_surface:
    st.subheader("Surface et consommation")
    st.caption("Échantillon aléatoire de 3 000 logements maximum de la sélection.")
    nuage = alt.Chart(resultats["nuage"]).mark_circle(size=30, opacity=0.5).encode(
        x=alt.X(f"{COL_SURFACE}:Q", title="Surface habitable (m²)"),
        y=alt.Y(f"{COL_CONSO}:Q", title=f"Consommation ({UNITE_CONSO})"),
        color=alt.Color(
            f"{COL_ETIQUETTE}:N",
            scale=alt.Scale(domain=ETIQUETTES, range=COULEURS_ETIQUETTES),
            title="Étiquette",
        ),
    )
    st.altair_chart(nuage)

with onglet_departements:
    st.subheader("Consommation moyenne par département")
    st.bar_chart(resultats["par_departement"])
