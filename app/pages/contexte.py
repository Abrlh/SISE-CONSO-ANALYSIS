"""Page « Contexte » : présente le jeu de données, sa qualité, le nettoyage, la carte et les filtres.

Cette page ne calcule rien : elle lit les tableaux pré-calculés (get_stat) et les affiche.
"""

import streamlit as st
from deps import get_service
from tableaux import lire_ou_arreter

import graphiques
from affichage import (
    COULEURS_ETIQUETTES, ETIQUETTES, choisir, filtres_perimetre, fmt_nombre, legende_etiquettes,
    liste_valeurs, nom_departement,
)

st.title("Contexte")

kpi = lire_ou_arreter("kpi_globaux")
apercu = lire_ou_arreter("apercu_donnees")
couverture = lire_ou_arreter("couverture_temporelle")

# ---- Ligne d'information sur les données : snapshot, date de téléchargement, départements
# Le snapshot est celui des statistiques affichées. La date est lue dans son identifiant (AAAA-MM-JJ_HHMMSS).
snapshot = get_service().snapshot_stats()
annee, mois, jour = (snapshot.split("_")[0].split("-") + ["", "", ""])[:3]
date_telechargement = f"{jour}/{mois}/{annee}" if annee else "date inconnue"
noms = [nom_departement(code) for code in liste_valeurs(kpi, "departement")]
st.caption(
    f"Données du snapshot {snapshot} (téléchargé le {date_telechargement}) "
    f"· départements : {', '.join(noms) if noms else 'non précisés'}"
)

# ---- Présentation du jeu de données
st.subheader("Présentation du jeu de données")
st.write(
    "Les diagnostics de performance énergétique (DPE) sont publiés par l'ADEME. Le jeu rassemble les logements "
    "existants et les logements neufs. Chaque ligne décrit un logement : sa surface, sa période de construction, "
    "son chauffage, la qualité de son isolation, sa consommation et son étiquette, de A (sobre) à G (énergivore)."
)

taille = choisir(apercu, "Tous")
dates = choisir(couverture, "Tous", "Tous")
colonnes = st.columns(4)
if taille.empty:
    colonnes[0].metric("Nombre de DPE", "n/a")
else:
    colonnes[0].metric("Nombre de DPE (après nettoyage)", fmt_nombre(taille.iloc[0]["nb_lignes"]))
    colonnes[2].metric("Colonnes", fmt_nombre(taille.iloc[0]["nb_colonnes"]))
colonnes[1].metric("Départements", fmt_nombre(len(liste_valeurs(kpi, "departement"))))
if dates.empty:
    colonnes[3].metric("Réception des DPE", "n/a")
else:
    colonnes[3].metric(
        "Dernière réception", str(dates.iloc[0]["date_max"])[:10],
        help=f"Les DPE les plus anciens datent du {str(dates.iloc[0]['date_min'])[:10]}.",
    )

# ---- Nettoyage et qualité des données
st.subheader("Nettoyage et qualité des données")
bilan = choisir(lire_ou_arreter("bilan_nettoyage"), "Tous")
if bilan.empty:
    st.info("Le bilan du nettoyage n'est pas disponible pour ce snapshot.")
else:
    with st.expander("Ce que le nettoyage a retiré, règle par règle", expanded=True):
        st.dataframe(
            bilan.sort_values("ordre")[["etape", "lignes", "lignes_retirees"]],
            hide_index=True,
            column_config={"etape": "Règle", "lignes": "Lignes après la règle", "lignes_retirees": "Lignes retirées"},
        )

retirees = choisir(lire_ou_arreter("colonnes_retirees"), "Tous")
if not retirees.empty:
    with st.expander("Colonnes retirées car trop vides"):
        st.dataframe(retirees[["colonne", "pct_manquant"]], hide_index=True,
                     column_config={"colonne": "Colonne", "pct_manquant": "% de cases vides avant retrait"})

qualite = choisir(lire_ou_arreter("qualite_donnees"), "Tous")
if qualite.empty:
    st.info("La qualité des données n'est pas disponible pour ce snapshot.")
else:
    presentes = qualite[qualite["presente"].astype(bool)]
    st.plotly_chart(graphiques.barres_manquants(
        presentes.nlargest(15, "pct_manquant"), "Les 15 colonnes les plus incomplètes (% de cases vides)"))

resume = choisir(lire_ou_arreter("stats_numeriques"), "Tous", "Tous")
if not resume.empty:
    with st.expander("Résumé statistique des variables numériques"):
        st.dataframe(resume.drop(columns=["departement", "origine"], errors="ignore"), hide_index=True)

# ---- Carte et filtres
st.subheader("Explorer la carte")
points = lire_ou_arreter("echantillon_points")
with st.expander("Filtres", expanded=True):
    departement, origine = filtres_perimetre(st, kpi)
    etiquettes = st.multiselect("Étiquettes DPE", ETIQUETTES, default=ETIQUETTES)
    # Bornes de surface = bornes du nettoyage (5 à 500 m²)
    surface = st.slider("Surface habitable (m²)", 5, 500, (5, 500))

colonne_surface = next((c for c in points.columns if "surface" in c), None)
masque = points["etiquette_dpe"].astype(str).isin(etiquettes)
if departement != "Tous":
    masque = masque & (points["departement"].astype(str) == departement)
if origine != "Tous":
    masque = masque & (points["origine"].astype(str) == origine)
if colonne_surface:
    masque = masque & points[colonne_surface].between(surface[0], surface[1])
selection = points[masque].dropna(subset=["latitude", "longitude"]).copy()

if selection.empty:
    st.warning("Aucun logement ne correspond à ces filtres : élargissez la sélection.")
else:
    couleurs = dict(zip(ETIQUETTES, COULEURS_ETIQUETTES))
    selection["couleur"] = selection["etiquette_dpe"].astype(str).map(couleurs)
    st.map(selection, latitude="latitude", longitude="longitude", color="couleur", size=60)
    legende_etiquettes()
    st.caption(
        f"{fmt_nombre(len(selection))} logements affichés (échantillon préparé en amont). "
        "Couleur = étiquette DPE."
    )

# ---- Rafraîchissement des données (branché plus tard sur le back end)
st.subheader("Rafraîchir les données")
with st.expander("Télécharger un nouveau snapshot depuis l'API ADEME"):
    st.write(
        "Cette action téléchargera à nouveau les DPE de chaque département depuis l'API de l'ADEME, "
        "puis relancera le nettoyage et le calcul des statistiques. Elle sera branchée sur le back end plus tard."
    )
    st.checkbox("Je confirme le téléchargement")
    st.button("Rafraîchir les données", disabled=True)

# ---- Aperçu
st.subheader("Aperçu des données")
st.dataframe(lire_ou_arreter("logements").head(20))

with st.expander("Limites des données"):
    st.markdown(
        "- Les chiffres décrivent **l'échantillon téléchargé**, pas l'ensemble du parc de logements.\n"
        "- Le téléchargement est plafonné à 100 000 lignes par jeu de données et par département, sans tirage aléatoire.\n"
        "- Les logements existants s'arrêtent en février 2026 alors que les neufs vont jusqu'à octobre 2026 : "
        "la répartition par année ne reflète pas une tendance réelle.\n"
        "- « Tous » désigne les départements téléchargés, pas la France entière.\n"
        "- Les immeubles entiers sont exclus : les statistiques concernent les maisons et les appartements.\n"
        "- Les DPE sont déclaratifs : certaines valeurs manquent ou sont aberrantes, d'où le nettoyage ci-dessus."
    )
