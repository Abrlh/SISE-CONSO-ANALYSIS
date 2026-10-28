"""Page « Statistiques » : chiffres clés et graphiques.

Cette page ne calcule rien : elle lit les tableaux pré-calculés (get_stat), choisit les lignes du
département et de l'origine demandés (« Tous » est déjà dans les tableaux) et les dessine.
"""

import streamlit as st
from tableaux import lire, lire_ou_arreter

import graphiques
from affichage import choisir, filtres_perimetre, fmt_nombre

st.title("Statistiques")

kpi = lire_ou_arreter("kpi_globaux")

# ---- Filtres
st.sidebar.header("Filtres")
departement, origine = filtres_perimetre(st.sidebar, kpi)


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


# ---- Export CSV des logements du périmètre (le fichier n'est préparé qu'au clic)
def csv_logements():
    tableau = choisir(lire("logements"), departement, origine)
    return tableau.to_csv(index=False).encode("utf-8")


st.download_button(
    "Exporter les données filtrées (CSV)", data=csv_logements, file_name="logements_filtres.csv",
    mime="text/csv", icon=":material/download:",
)

# ---- Chiffres clés
colonnes = st.columns(5)
colonnes[0].metric("Logements", fmt_nombre(ligne["nb_logements"]))
colonnes[1].metric("Consommation médiane", f"{ligne['conso_mediane']:.0f} kWh/m²/an")
colonnes[2].metric("Surface médiane", f"{ligne['surface_mediane']:.0f} m²")
colonnes[3].metric("Passoires (F-G)", f"{ligne['part_f_g']:.1f} %",
                   help="Part des logements d'étiquette F ou G.")
colonnes[4].metric("Étiquettes A-B", f"{ligne['part_a_b']:.1f} %")
st.caption("Consommations en kWh/m²/an (énergie primaire). Médianes : elles ne sont pas tirées par les valeurs extrêmes.")

onglets = st.tabs(["Vue d'ensemble", "Consommation", "Facteurs", "Coût et GES", "Dans le temps"])

# ---- Vue d'ensemble
with onglets[0]:
    repartition = choisir(lire_ou_arreter("repartition_etiquettes"), departement, origine)
    if not vide(repartition):
        gauche, droite = st.columns(2)
        gauche.plotly_chart(graphiques.barres_etiquettes(
            repartition, "pourcentage", "Répartition des étiquettes DPE (%)", "% des logements"))
        droite.plotly_chart(graphiques.anneau(repartition, "Poids de chaque étiquette"))

# ---- Consommation
with onglets[1]:
    distribution = choisir(lire_ou_arreter("distribution_conso"), departement, origine)
    if not vide(distribution):
        st.plotly_chart(graphiques.histogramme(distribution, "Distribution de la consommation"))

    par_energie = choisir(lire_ou_arreter("conso_par_etiquette"), departement, origine)
    if not vide(par_energie):
        st.plotly_chart(graphiques.conso_par_energie(
            par_energie, "Consommation médiane par étiquette et énergie de chauffage"))

    resume = choisir(lire_ou_arreter("stats_conso"), departement, origine)
    if not resume.empty:
        with st.expander("Résumé statistique de la consommation"):
            st.dataframe(resume.drop(columns=["departement", "origine"], errors="ignore"), hide_index=True)

# ---- Facteurs
with onglets[2]:
    modalites = lire_ou_arreter("conso_par_modalite")
    variables = sorted(modalites["variable"].astype(str).unique())
    if not variables:
        st.info("Données non disponibles.")
    else:
        variable = st.selectbox("Caractéristique du logement", variables)
        conso = choisir(modalites, departement, origine)
        conso = conso[conso["variable"].astype(str) == variable].sort_values("ordre")
        if not vide(conso):
            st.plotly_chart(graphiques.barres_modalites(conso, f"Consommation médiane selon : {variable}"))
        etiquettes = choisir(lire_ou_arreter("etiquette_par_modalite"), departement, origine)
        etiquettes = etiquettes[etiquettes["variable"].astype(str) == variable].sort_values("ordre")
        if not etiquettes.empty:
            st.plotly_chart(graphiques.barres_empilees(etiquettes, f"Étiquettes selon : {variable}"))

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
        st.plotly_chart(graphiques.chaleur(ges, "Étiquette GES selon l'étiquette DPE (% par ligne)"))

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
        st.plotly_chart(graphiques.courbe(temps, "part_f_g", "Part de passoires (F-G) par année", "% de F et G"))
