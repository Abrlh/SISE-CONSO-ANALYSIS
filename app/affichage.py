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


def widgets_filtres(conteneur, departements, origines):
    """Affiche les filtres dans le conteneur donné (st.sidebar ou st). Ils ne modifient encore rien."""
    conteneur.selectbox(
        "Département",
        ["Tous"] + departements,
        format_func=lambda code: code if code == "Tous" else nom_departement(code),
    )
    conteneur.radio("Origine du logement", ["Tous"] + origines)
    conteneur.multiselect("Étiquettes DPE", ETIQUETTES, default=ETIQUETTES)
    conteneur.slider("Surface habitable (m²)", 5, 500, (5, 500))


def a_venir(titre, detail="Ce graphique sera affiché avec les résultats préparés par le back end."):
    """Emplacement d'un graphique ou d'un chiffre qui sera branché plus tard."""
    with st.container(border=True):
        st.markdown(f"**{titre}**")
        st.caption(f"À venir. {detail}")
