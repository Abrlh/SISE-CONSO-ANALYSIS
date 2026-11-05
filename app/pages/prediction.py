"""Page « Prédiction » : formulaire de saisie d'un logement et estimation.

Les champs du formulaire et leurs choix viennent des modèles entraînés (AppService.formulaire),
l'estimation de AppService.predire. L'apprentissage sera branché plus tard.
"""

import pandas as pd
import streamlit as st

from affichage import nom_departement
from deps import get_service

st.title("Prédiction")
st.write("Décrivez un logement pour estimer son étiquette DPE et sa consommation.")

service = get_service()
try:
    formulaire = service.formulaire()
except FileNotFoundError as erreur:
    st.error(f"Modèles introuvables : {erreur}")
    st.stop()

# choix proposé à l'utilisateur -> tâches à lancer
ESTIMATIONS = {
    "Étiquette DPE": ["classification"],
    "Consommation": ["regression"],
    "Les deux": ["classification", "regression"],
}


def champs_des_modeles(taches, departement):
    """Champs attendus par les modèles demandés pour ce département, réunis."""
    champs = {}
    for tache in taches:
        champs.update(formulaire[tache][departement]["champs"])
    return champs


def afficher_champ(colonne, champ):
    """Affiche le widget d'un champ et renvoie la valeur saisie (None tant que rien n'est saisi)."""
    libelle = colonne.replace("_", " ").capitalize()
    # key=colonne : permet de préremplir le champ via st.session_state (bouton de test)
    if champ["type"] == "choix":
        return st.selectbox(libelle, champ["choix"], index=None, placeholder="Choisir une valeur", key=colonne)
    return st.number_input(libelle, min_value=champ["min"], max_value=champ["max"], value=None,
                           placeholder=f"entre {champ['min']:g} et {champ['max']:g}", key=colonne)


# TODO à supprimer : bouton de test qui remplit le formulaire avec des données fictives
def remplir_test(champs):
    """Met une valeur fictive dans chaque champ : 1re valeur des listes, minimum des nombres sauf exceptions."""
    valeurs = {"surface_habitable_logement": 60.0, "annee_construction": 1975.0}
    for colonne, champ in champs.items():
        if champ["type"] == "choix":
            st.session_state[colonne] = champ["choix"][0]
        else:
            st.session_state[colonne] = valeurs.get(colonne, champ["min"])


def afficher_precision(tache, departement):
    """Scores du modèle sur le jeu de test, comparés à une référence naïve."""
    scores = service.evaluation_modele(tache, departement, "scores")
    st.dataframe(
        scores[["libelle", "valeur", "reference_naive", "unite"]].round(2),
        column_config={"libelle": "Mesure", "valeur": "Modèle", "reference_naive": "Référence naïve",
                       "unite": "Unité"},
        hide_index=True,
    )


gauche, droite = st.columns([3, 2])

with gauche:
    # hors du formulaire : changer ces choix met à jour les champs tout de suite
    choix = st.radio("Estimer", list(ESTIMATIONS), horizontal=True)
    taches = ESTIMATIONS[choix]
    # seulement les départements qui ont un modèle pour chaque tâche demandée
    departements = sorted(set.intersection(*(set(formulaire[t]) for t in taches)))
    if not departements:
        st.warning("Aucun département n'a de modèle pour cette estimation.")
        st.stop()
    departement = st.selectbox("Département", departements, format_func=nom_departement)
    champs = champs_des_modeles(taches, departement)

    # TODO à supprimer avec remplir_test
    st.button("Test : remplir avec des données fictives", on_click=remplir_test, args=(champs,))

    with st.form("formulaire_logement"):
        st.subheader("Caractéristiques du logement")
        saisies = {colonne: afficher_champ(colonne, champ) for colonne, champ in champs.items()}
        envoye = st.form_submit_button("Estimer ce logement")

with droite:
    st.subheader("Résultat")
    if not envoye:
        st.caption("Remplissez le formulaire puis cliquez sur « Estimer ce logement ».")
    else:
        # un champ numérique vide ferait passer sa colonne en texte : la prédiction serait fausse sans erreur
        manquants = [colonne for colonne, valeur in saisies.items() if valeur is None]
        if manquants:
            st.warning("Champs à remplir : " + ", ".join(c.replace("_", " ") for c in manquants))
        else:
            X = pd.DataFrame([saisies])
            if "classification" in taches:
                etiquette = service.predire("classification", departement, X)[0]
                st.metric("Étiquette DPE estimée", etiquette)
                afficher_precision("classification", departement)
            if "regression" in taches:
                conso = service.predire("regression", departement, X)[0]
                st.metric("Consommation estimée", f"{conso:.0f} kWh/m²/an")
                afficher_precision("regression", departement)

    st.subheader("Modèles")
    st.write("Relancer l'apprentissage utilise les données les plus récentes et peut prendre quelques minutes.")
    if st.button("Relancer l'apprentissage", icon=":material/refresh:"):
        st.info("L'apprentissage sera disponible quand les modèles seront branchés sur l'application.")
