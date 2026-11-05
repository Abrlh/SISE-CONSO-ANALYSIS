"""Page « Prédiction » : formulaire de saisie d'un logement.

Les champs du formulaire et leurs choix viennent des modèles entraînés (AppService.formulaire).
Page de saisie uniquement : le calcul de l'estimation et l'apprentissage seront branchés plus tard.
"""

import streamlit as st

from affichage import nom_departement
from deps import get_service

st.title("Prédiction")
st.write("Décrivez un logement pour estimer son étiquette DPE et sa consommation.")

try:
    formulaire = get_service().formulaire()
except FileNotFoundError as erreur:
    st.error(f"Modèles introuvables : {erreur}")
    st.stop()


def champs_du_departement(departement):
    """Champs attendus par les modèles de classification et de régression du département, réunis."""
    champs = {}
    for tache in ("classification", "regression"):
        champs.update(formulaire[tache].get(departement, {}).get("champs", {}))
    return champs


def afficher_champ(colonne, champ):
    """Affiche le widget d'un champ et renvoie la valeur saisie (None tant que rien n'est saisi)."""
    libelle = colonne.replace("_", " ").capitalize()
    if champ["type"] == "choix":
        return st.selectbox(libelle, champ["choix"], index=None, placeholder="Choisir une valeur")
    return st.number_input(libelle, min_value=champ["min"], max_value=champ["max"], value=None,
                           placeholder=f"entre {champ['min']:g} et {champ['max']:g}")


gauche, droite = st.columns([3, 2])

with gauche:
    # hors du formulaire : changer de département met à jour les champs tout de suite
    departements = sorted(set(formulaire["classification"]) | set(formulaire["regression"]))
    departement = st.selectbox("Département", departements, format_func=nom_departement)

    with st.form("formulaire_logement"):
        st.subheader("Caractéristiques du logement")
        saisies = {colonne: afficher_champ(colonne, champ)
                   for colonne, champ in champs_du_departement(departement).items()}
        envoye = st.form_submit_button("Estimer ce logement")

with droite:
    st.subheader("Résultat")
    if envoye:
        st.info("L'estimation sera disponible quand les modèles seront branchés sur l'application.")
    else:
        st.caption("Remplissez le formulaire puis cliquez sur « Estimer ce logement ».")

    st.subheader("Modèles")
    st.write("Relancer l'apprentissage utilise les données les plus récentes et peut prendre quelques minutes.")
    if st.button("Relancer l'apprentissage", icon=":material/refresh:"):
        st.info("L'apprentissage sera disponible quand les modèles seront branchés sur l'application.")
