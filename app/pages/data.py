"""Page « Contexte » : présente les données DPE et les indicateurs clés (KPI).

Cette page ne calcule rien : elle demande les chiffres à AppService (service.get_stats) et les affiche.
"""

import streamlit as st
from deps import get_service

from src.analysis import NOMS_DEPARTEMENTS, UNITE_CONSO


def fmt_nombre(valeur, decimales=0):
    """Met un nombre en forme à la française (386450 -> '386 450'). Renvoie 'n/a' si la valeur est absente."""
    if valeur is None:
        return "n/a"
    return f"{valeur:,.{decimales}f}".replace(",", " ")


service = get_service()

st.title("Contexte")
st.write(
    "Cette application analyse les diagnostics de performance énergétique (DPE) publiés par l'ADEME "
    "pour répondre à la question d'Enedis : **quel est le lien entre l'étiquette DPE d'un logement "
    "et sa consommation d'énergie ?**"
)

# Si les données prétraitées sont absentes, on explique le problème au lieu de planter
try:
    stats = service.get_stats()
except (FileNotFoundError, ValueError) as erreur:
    st.error(f"Impossible de charger les données : {erreur}")
    st.stop()

kpi = stats["kpi"]
noms = [f"{NOMS_DEPARTEMENTS.get(code, code)} ({code})" for code in stats["departements"]]

st.caption(
    f"Données du snapshot {stats['snapshot_id']} (téléchargé le {stats['snapshot_date']}) "
    f"· départements : {', '.join(noms) if noms else 'non précisés'}"
)

# Indicateurs clés
st.subheader("Indicateurs clés")
colonnes = st.columns(5)

colonnes[0].metric("Nombre de DPE", fmt_nombre(kpi["nb_dpe"]))
colonnes[1].metric(
    "Conso moyenne",
    fmt_nombre(kpi["conso_moyenne"]),
    help=f"Médiane : {fmt_nombre(kpi['conso_mediane'])} {UNITE_CONSO}. "
         "La médiane est moins sensible aux valeurs extrêmes.",
)
colonnes[2].metric(
    "Part de F et G",
    "n/a" if kpi["part_fg"] is None else f"{kpi['part_fg'] * 100:.1f} %",
)
colonnes[3].metric("Étiquette dominante", kpi["etiquette_frequente"] or "n/a")
colonnes[4].metric("Écart G vs A", fmt_nombre(kpi["ecart_g_vs_a"]))
st.caption(f"Consommations en {UNITE_CONSO} (énergie primaire). Écart G vs A = conso moyenne des G moins celle des A.")

# Lien entre l'étiquette et la consommation
gauche, droite = st.columns(2)
with gauche:
    st.subheader("Répartition des étiquettes DPE")
    st.bar_chart(stats["repartition_etiquettes"])
with droite:
    st.subheader("Consommation moyenne par étiquette")
    st.bar_chart(stats["conso_par_etiquette"])

with st.expander("Limites des données"):
    st.markdown(
        "- Les chiffres décrivent **l'échantillon téléchargé**, pas l'ensemble du parc de logements.\n"
        "- Le téléchargement est plafonné par département : seuls certains départements sont couverts.\n"
        "- Les logements neufs pèsent très différemment selon le département : comparer avec prudence.\n"
        "- Les logements classés « immeuble » sont exclus du nettoyage.\n"
        "- Détail des règles : `docs/nettoyage_donnees.md`."
    )

st.subheader("Aperçu des données")
st.dataframe(service.get_apercu(20))
