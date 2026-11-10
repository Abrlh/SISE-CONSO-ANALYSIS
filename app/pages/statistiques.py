"""Page « Statistiques » : chiffres clés et graphiques.

Cette page ne calcule rien : elle lit les tableaux pré-calculés (get_stat), choisit les lignes du
département et de l'origine demandés (« Tous » est déjà dans les tableaux) et les dessine.
"""

import streamlit as st
from tableaux import lire, lire_ou_arreter

import graphiques
from affichage import (
    NOMS_COLONNES_APERCU, NOMS_COLONNES_STATS, NOMS_VARIABLES_COURTS, choisir, filtres_perimetre, fmt_nombre,
)
from style import habiller_chiffres_statistiques, habiller_filtres

st.title(":material/bar_chart: Statistiques")

kpi = lire_ou_arreter("kpi_globaux")

# ---- Filtres : bande en haut de la page
habiller_filtres()
bande = st.container(border=True, horizontal=True, vertical_alignment="center", key="bande_filtres")
bande.markdown("**:material/filter_alt: Filtres**")
departement, origine = filtres_perimetre(bande, kpi)
filtre_departement = None if departement == "Tous" else departement
filtre_origine = None if origine == "Tous" else origine


def vide(tableau):
    """Affiche un message et renvoie True si le tableau n'a aucune ligne pour ce périmètre."""
    if tableau.empty:
        st.info("Données non disponibles pour cette sélection.")
        return True
    return False


# ---- Nombre de logements concernés
ligne = choisir(kpi, departement, origine)
total = choisir(kpi, "Tous", "Tous")
if ligne.empty:
    st.warning("Aucun logement ne correspond à cette sélection.")
    st.stop()
ligne = ligne.iloc[0]
if not total.empty:
    st.caption(
        f"{fmt_nombre(ligne['nb_logements'])} logements sur {fmt_nombre(total.iloc[0]['nb_logements'])} "
        "correspondent aux filtres choisis."
    )


def csv_logements():
    """Les logements du périmètre choisi, au format CSV (le calcul se fait au clic sur le bouton)."""
    tableau = choisir(lire("logements"), filtre_departement, filtre_origine)
    return tableau.to_csv(index=False).encode("utf-8")


st.download_button(
    "Exporter les données filtrées (CSV)", data=csv_logements, file_name="logements_filtres.csv",
    mime="text/csv", icon=":material/download:",
)


# ---- Chiffres clés
habiller_chiffres_statistiques()
with st.container(key="chiffres_stats"):
    colonnes = st.columns(5)
    colonnes[0].metric(":material/home: Logements", fmt_nombre(ligne["nb_logements"]))
    colonnes[1].metric(
        ":material/bolt: Consommation médiane", f"{ligne['conso_mediane']:.0f}",
        help="Médiane de la consommation d'énergie de 5 usages par m² (kWh/m²/an).",
    )
    colonnes[2].metric(
        ":material/square_foot: Surface médiane", f"{ligne['surface_mediane']:.0f}",
        help="Surface habitable médiane des logements, en m².",
    )
    colonnes[3].metric(":material/warning: Passoires (F-G)", f"{ligne['part_f_g']:.1f} %",
                       help="Part des logements d'étiquette F ou G.")
    colonnes[4].metric(":material/eco: Étiquettes A-B", f"{ligne['part_a_b']:.1f} %")

onglets = st.tabs([
    ":material/pie_chart: Vue d'ensemble", ":material/bolt: Consommation", ":material/tune: Facteurs",
    ":material/euro: Coût et GES", ":material/trending_up: Dans le temps",
])

# ---- Vue d'ensemble
with onglets[0]:
    repartition = choisir(lire_ou_arreter("repartition_etiquettes"), departement, origine)
    if not vide(repartition):
        gauche, droite = st.columns(2)
        gauche.plotly_chart(graphiques.barres_etiquettes(
            repartition, "pourcentage", "Répartition des étiquettes DPE (%)", "% des logements"))
        droite.plotly_chart(graphiques.anneau(repartition, "Poids de chaque étiquette"))

    st.subheader(":material/compare_arrows: Comparer les départements")
    gauche, droite = st.columns(2)
    gauche.plotly_chart(graphiques.barres_departements(
        kpi, "conso_mediane", "Consommation médiane par département", "Consommation médiane (kWh/m²/an)"),)
    droite.plotly_chart(graphiques.barres_departements(
        kpi, "part_f_g", "Part de passoires (F-G) par département", "% de logements F ou G", ".1f"),)
    st.caption("Ces graphiques comparent tous les départements : ils ne dépendent pas des filtres.")

    

# ---- Consommation
with onglets[1]:
    distribution = choisir(lire_ou_arreter("distribution_conso"), departement, None)
    distribution = distribution[distribution["origine"].astype(str) != "Tous"]
    if not vide(distribution):
        st.plotly_chart(graphiques.histogramme_origines(
            distribution, "Distribution de la consommation : logements existants et neufs"),)
        st.caption("Ce graphique compare toujours les logements existants et neufs : il ne dépend que du département.")

    points = choisir(lire_ou_arreter("echantillon_points"), filtre_departement, filtre_origine)
    if not vide(points):
        st.plotly_chart(graphiques.nuage_surface_conso(points, "Consommation selon la surface"))
        st.caption(f"Chaque point est un logement de l'échantillon préparé en amont ({fmt_nombre(len(points))} affichés).")

    resume = choisir(lire_ou_arreter("stats_conso"), departement, origine)
    if not resume.empty:
        with st.expander("Résumé statistique de la consommation"):
            st.caption("Consommation d'énergie de 5 usages par m² (kWh/m²/an).")
            tableau = resume.drop(columns=["departement", "origine"], errors="ignore").rename(
                columns=NOMS_COLONNES_STATS
            )
            tableau = tableau[[c for c in ["Effectif", "Moyenne", "Écart-type", "Médiane"] if c in tableau.columns]]
            st.dataframe(tableau, hide_index=True)

# ---- Facteurs
with onglets[2]:
    modalites = lire_ou_arreter("conso_par_modalite")
    variables = sorted(modalites["variable"].astype(str).unique())
    if not variables:
        st.info("Données non disponibles.")
    else:
        # Affichage seulement : le nom lisible remplace le nom de la base dans la liste et les titres
        variable = st.selectbox(
            "Caractéristique du logement", variables, format_func=lambda code: NOMS_COLONNES_APERCU.get(code, code)
        )
        nom_variable = NOMS_COLONNES_APERCU.get(variable, variable)
        conso = choisir(modalites, departement, origine)
        conso = conso[conso["variable"].astype(str) == variable].sort_values("ordre")
        etiquettes = choisir(lire_ou_arreter("etiquette_par_modalite"), departement, origine)
        etiquettes = etiquettes[etiquettes["variable"].astype(str) == variable].sort_values("ordre")
        gauche, droite = st.columns(2)
        with gauche:
            if not vide(conso):
                st.plotly_chart(graphiques.barres_modalites(conso, f"Consommation médiane selon : {nom_variable}"))
        with droite:
            if not etiquettes.empty:
                st.plotly_chart(graphiques.barres_empilees(etiquettes, f"Étiquettes selon : {nom_variable}"))

        st.subheader(":material/grid_on: Corrélations entre les variables numériques")
        correlations = choisir(lire_ou_arreter("correlations"), None, origine)
        if not vide(correlations):
            correlations = correlations.copy()
            # Affichage seulement : on remplace les noms de la base par des noms lisibles
            for colonne in ["variable_x", "variable_y"]:
                correlations[colonne] = correlations[colonne].map(lambda code: NOMS_VARIABLES_COURTS.get(code, code))
            st.plotly_chart(graphiques.matrice_correlation(correlations, "Matrice de corrélation"))
            with st.expander("Plus de détails"):
                st.markdown(
                    "- Plus la case est foncée, plus le lien entre les deux variables est fort.\n"
                    "- Chaque case est comprise entre -1 et 1. Proche de 1 : les deux variables montent ensemble. "
                    "Proche de -1 : l'une monte quand l'autre baisse. Proche de 0 : pas de lien.\n"
                    "- La matrice dépend de l'origine choisie, pas du département."
                )


# ---- Coût et GES
with onglets[3]:
    cout = choisir(lire_ou_arreter("cout_ges_par_etiquette"), departement, origine)
    if not vide(cout):
        gauche, droite = st.columns(2)
        gauche.plotly_chart(graphiques.barres_etiquettes(
            cout, "cout_par_m2_median", "Coût médian par m²", "Coût par m² (unité de la source)"))
        droite.plotly_chart(graphiques.barres_etiquettes(
            cout, "ges_median", "Émissions de GES médianes", "Émissions de GES"))
        st.caption("Le coût est dans l'unité de la source : à utiliser pour comparer les étiquettes entre elles.")
    ges = choisir(lire_ou_arreter("etiquette_ges_vs_dpe"), None, origine)
    if not ges.empty:
        gauche, droite = st.columns(2)
        gauche.plotly_chart(graphiques.ges_selon_dpe(ges, "Étiquette GES selon l'étiquette DPE"))
        gauche.caption("Lecture : chaque barre représente 100 logements d'une même étiquette DPE, répartis selon leur étiquette GES.")
        droite.plotly_chart(graphiques.camembert_ges(ges, "Répartition des logements par étiquette GES"))
        st.caption("Ces deux graphiques dépendent de l'origine choisie, pas du département.")

# ---- Dans le temps
with onglets[4]:
    st.warning(
        "À lire avec prudence : le téléchargement est plafonné et non aléatoire, et les logements existants "
        "s'arrêtent en février 2026. Cette évolution ne montre pas une tendance réelle du parc."
    )
    temps = choisir(lire_ou_arreter("evolution_annuelle"), departement, origine)
    if not vide(temps):
        gauche, droite = st.columns(2)
        gauche.plotly_chart(graphiques.barres_annuelles(temps, "Logements par année de réception"))
        droite.plotly_chart(graphiques.courbe(
            temps, "conso_mediane", "Consommation médiane par année", "Consommation médiane (kWh/m²/an)"))
        st.plotly_chart(graphiques.courbe(temps, "part_f_g", "Part de passoires (F-G) par année", "% de F et G", couleur=graphiques.ORANGE))