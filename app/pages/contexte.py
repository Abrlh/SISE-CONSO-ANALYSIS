"""Page « Contexte » : présente le jeu de données, la carte, les filtres et le rafraîchissement.

Cette page ne calcule rien : elle lit les tableaux pré-calculés (get_stat) et les affiche.
"""

import streamlit as st
from deps import get_service
from tableaux import lire_ou_arreter

from affichage import (
    COULEURS_ETIQUETTES, ETIQUETTES, NOMS_VARIABLES_NUMERIQUES, choisir, filtres_perimetre, fmt_nombre,
    legende_etiquettes, liste_valeurs, nom_departement,
)
from reentrainement import afficher_bloc_rafraichissement
from style import habiller_contexte, ligne_snapshot

habiller_contexte()

st.title(":material/dataset: Contexte")

kpi = lire_ou_arreter("kpi_globaux")
apercu = lire_ou_arreter("apercu_donnees")
couverture = lire_ou_arreter("couverture_temporelle")

def date_fr(texte):
    """« 2026-10-05... » devient « 05/10/2026 » (affichage seulement)."""
    morceaux = str(texte)[:10].split("-")
    return "/".join(reversed(morceaux)) if len(morceaux) == 3 else str(texte)[:10]


# ---- Ligne d'information sur les données : snapshot, date de téléchargement, départements
# Le snapshot est celui des statistiques affichées. La date est lue dans son identifiant (AAAA-MM-JJ_HHMMSS).
snapshot = get_service().snapshot_stats()
annee, mois, jour = (snapshot.split("_")[0].split("-") + ["", "", ""])[:3]
date_telechargement = f"{jour}/{mois}/{annee}" if annee else "date inconnue"
noms = [nom_departement(code) for code in liste_valeurs(kpi, "departement")]
st.markdown(ligne_snapshot(snapshot, date_telechargement, noms), unsafe_allow_html=True)

# ---- Présentation du jeu de données
with st.container(key="ruban_presentation"):
    st.subheader(":material/info: Présentation du jeu de données")
st.write(
    "Les diagnostics de performance énergétique (DPE) sont publiés par l'ADEME. Le jeu rassemble les logements "
    "existants et les logements neufs. Chaque ligne décrit un logement : sa surface, sa période de construction, "
    "son chauffage, la qualité de son isolation, sa consommation et son étiquette, de A (sobre) à G (énergivore)."
)

taille = choisir(apercu, "Tous")
dates = choisir(couverture, "Tous", "Tous")
# les quatre chiffres sont dans un conteneur nommé « chiffres » pour que le style les colore
with st.container(key="chiffres"):
    colonnes = st.columns(4)
    if taille.empty:
        colonnes[0].metric(":material/apartment: Nombre de DPE", "n/a")
    else:
        colonnes[0].metric(
            ":material/apartment: Nombre de DPE", fmt_nombre(taille.iloc[0]["nb_lignes"]), help="Nombre de logements après nettoyage."
        )
        colonnes[2].metric(":material/view_column: Colonnes", fmt_nombre(taille.iloc[0]["nb_colonnes"]))
    colonnes[1].metric(":material/location_on: Départements", fmt_nombre(len(liste_valeurs(kpi, "departement"))))
    if dates.empty:
        colonnes[3].metric(":material/calendar_month: Dernière réception", "n/a")
    else:
        colonnes[3].metric(
            ":material/calendar_month: Dernière réception", date_fr(dates.iloc[0]["date_max"]),
            help=f"Les DPE les plus anciens datent du {date_fr(dates.iloc[0]['date_min'])}.",
        )

# ---- Résumé statistique des variables numériques
resume = choisir(lire_ou_arreter("stats_numeriques"), "Tous", "Tous")
if not resume.empty:
    with st.expander("Résumé statistique des variables numériques", icon=":material/functions:"):
        st.caption(
            "Consommation en énergie primaire. Les 5 usages comptabilisés : chauffage, eau chaude, refroidissement, "
            "éclairage et auxiliaires (ventilateurs, pompes)."
        )
        tableau = resume.drop(columns=["departement", "origine"], errors="ignore").copy()
        # la colonne des valeurs manquantes n'est plus affichée
        tableau = tableau.loc[:, ~tableau.columns.str.contains("manquant", case=False)]
        # On remplace le nom de la base par un nom lisible (affichage seulement)
        tableau["variable"] = tableau["variable"].map(lambda code: NOMS_VARIABLES_NUMERIQUES.get(code, code))
        st.dataframe(
            tableau, hide_index=True,
            column_config={"variable": st.column_config.TextColumn("Variable", width="large")},
        )

# ---- Carte et filtres
with st.container(key="ruban_carte"):
    st.subheader(":material/map: Explorer la carte")
points = lire_ou_arreter("echantillon_points")
with st.expander("Filtres", expanded=True):
    departement, origine = filtres_perimetre(st, kpi)
    etiquettes = st.multiselect("Étiquettes DPE", ETIQUETTES, default=ETIQUETTES)
    # Bornes de surface = bornes du nettoyage (5 à 500 m²)
    # conteneur « surface » : le style fait passer ce curseur en rouge
    with st.container(key="surface"):
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

# ---- Rafraîchissement des données (lance toute la pipeline sur GitHub Actions, voir app/reentrainement.py)
with st.container(key="ruban_rafraichir"):
    st.subheader(":material/refresh: Rafraîchir les données")
with st.expander("Télécharger un nouveau snapshot depuis l'API ADEME"):
    st.write(
        "Cette action télécharge à nouveau les DPE de chaque département depuis l'API de l'ADEME, "
        "puis relance le nettoyage, le calcul des statistiques et l'apprentissage des modèles."
    )
    afficher_bloc_rafraichissement(snapshot)

# ---- Aperçu
with st.container(key="ruban_apercu"):
    st.subheader(":material/table_chart: Aperçu des données")
# Les 20 lignes sont tirées au hasard parmi les logements sélectionnés par les filtres ci-dessus
# (random_state fixe : le tirage ne change pas à chaque clic)
if selection.empty:
    st.info("Aucun logement à afficher avec ces filtres.")
else:
    apercu_lignes = selection.drop(columns=["couleur"], errors="ignore")
    st.dataframe(apercu_lignes.sample(min(20, len(apercu_lignes)), random_state=0), hide_index=True)

with st.expander("Limites des données", icon=":material/warning:"):
    st.markdown(
        "- Les chiffres décrivent **l'échantillon téléchargé**, pas l'ensemble du parc de logements.\n"
        "- Le téléchargement est plafonné à 100 000 lignes par jeu de données et par département, sans tirage aléatoire.\n"
        "- Les logements existants s'arrêtent en février 2026 alors que les neufs vont jusqu'à octobre 2026 : "
        "la répartition par année ne reflète pas une tendance réelle.\n"
        "- « Tous » désigne les départements téléchargés, pas la France entière.\n"
        "- Les immeubles entiers sont exclus : les statistiques concernent les maisons et les appartements.\n"
        "- Les DPE sont déclaratifs : certaines valeurs manquent ou sont aberrantes, d'où un nettoyage avant analyse."
    )