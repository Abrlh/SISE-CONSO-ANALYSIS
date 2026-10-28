"""Éléments d'affichage partagés par les pages."""

import streamlit as st

# Étiquettes DPE de A (très performant) à G (très énergivore)
ETIQUETTES = ["A", "B", "C", "D", "E", "F", "G"]

# Couleurs des étiquettes, de A (vert) à G (rouge), dans le même ordre que ETIQUETTES
COULEURS_ETIQUETTES = ["#319834", "#33cc31", "#cbfc34", "#fbfe06", "#fccc05", "#fc9935", "#fc0205"]

# Noms des départements du projet
NOMS_DEPARTEMENTS = {"59": "Nord", "69": "Rhône", "75": "Paris"}

# Illustration de la page d'accueil : une maison et l'échelle des étiquettes
ILLUSTRATION_SVG = """
<svg viewBox="0 0 340 220" width="100%" role="img" aria-label="Maison et échelle des étiquettes DPE de A à G">
  <path d="M20 120 100 50l80 70v80H20z" fill="#FFFFFF" stroke="#0F766E" stroke-width="3" stroke-linejoin="round"/>
  <rect x="82" y="150" width="36" height="50" fill="#0F766E"/>
  <rect x="44" y="124" width="28" height="24" fill="#BFD9D4"/>
  <rect x="128" y="124" width="28" height="24" fill="#BFD9D4"/>
  <rect x="200" y="30" width="60" height="20" rx="3" fill="#319834"/>
  <rect x="200" y="54" width="75" height="20" rx="3" fill="#33CC31"/>
  <rect x="200" y="78" width="90" height="20" rx="3" fill="#CBFC34"/>
  <rect x="200" y="102" width="105" height="20" rx="3" fill="#FBFE06"/>
  <rect x="200" y="126" width="120" height="20" rx="3" fill="#FBCC05"/>
  <rect x="200" y="150" width="120" height="20" rx="3" fill="#FC9935"/>
  <rect x="200" y="174" width="120" height="20" rx="3" fill="#FC0205"/>
</svg>
"""


def nom_departement(code):
    """Nom lisible d'un département, ex. '59' -> 'Nord (59)'."""
    return f"{NOMS_DEPARTEMENTS.get(code, code)} ({code})"


def liste_valeurs(tableau, colonne):
    """Valeurs distinctes d'une colonne, triées, sans la valeur « Tous »."""
    return sorted(v for v in tableau[colonne].astype(str).unique() if v != "Tous")


def filtres_perimetre(conteneur, tableau_perimetres):
    """Affiche les filtres Département et Origine, d'après un tableau qui a ces deux colonnes (kpi_globaux).

    Renvoie (département, origine). La valeur « Tous » veut dire « tous confondus ».
    """
    departement = conteneur.selectbox(
        "Département",
        ["Tous"] + liste_valeurs(tableau_perimetres, "departement"),
        format_func=lambda code: code if code == "Tous" else nom_departement(code),
    )
    origine = conteneur.radio("Origine du logement", ["Tous"] + liste_valeurs(tableau_perimetres, "origine"))
    return departement, origine


def choisir(tableau, departement=None, origine=None):
    """Sélectionne les lignes d'un tableau pour un département et/ou une origine. Aucun calcul."""
    masque = tableau.index == tableau.index
    if departement is not None and "departement" in tableau.columns:
        masque = masque & (tableau["departement"].astype(str) == departement)
    if origine is not None and "origine" in tableau.columns:
        masque = masque & (tableau["origine"].astype(str) == origine)
    return tableau[masque]


def fmt_nombre(valeur, decimales=0):
    """Met un nombre en forme à la française (388717 -> '388 717')."""
    return f"{valeur:,.{decimales}f}".replace(",", " ")


def legende_etiquettes():
    """Légende des couleurs des étiquettes, en une ligne."""
    elements = [
        f"<span style='display:inline-block;width:12px;height:12px;border-radius:50%;"
        f"background:{couleur};margin-right:4px'></span>{lettre}"
        for lettre, couleur in zip(ETIQUETTES, COULEURS_ETIQUETTES)
    ]
    st.markdown("&nbsp;&nbsp;&nbsp;".join(elements), unsafe_allow_html=True)


def a_venir(titre, detail="Ce graphique sera affiché avec les résultats préparés par le back end."):
    """Emplacement d'un graphique ou d'un chiffre qui sera branché plus tard."""
    with st.container(border=True):
        st.markdown(f"**{titre}**")
        st.caption(f"À venir. {detail}")
