"""Page « Prédiction » : formulaire de saisie d'un logement et estimation.

Les champs du formulaire et leurs choix viennent des modèles entraînés (AppService.formulaire),
l'estimation de AppService.predire. L'apprentissage sera branché plus tard.
"""

import pandas as pd
import streamlit as st

from affichage import CHAMPS_ENTIERS, GROUPES_CHAMPS, NOMS_CHAMPS, nom_departement
from deps import get_service
from style import echelle_dpe, habiller_prediction

st.title(":material/online_prediction: Prédiction")
st.write("Décrivez un logement pour estimer son étiquette DPE et sa consommation.")
habiller_prediction()

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
TITRES_TACHES = {"classification": "Étiquette DPE", "regression": "Consommation"}


def champs_des_modeles(taches, departement):
    """Champs attendus par les modèles demandés pour ce département, réunis."""
    champs = {}
    for tache in taches:
        champs.update(formulaire[tache][departement]["champs"])
    return champs


def libelle(colonne):
    """Nom lisible d'un champ (à défaut, le nom de la colonne sans les tirets bas)."""
    return NOMS_CHAMPS.get(colonne, colonne.replace("_", " ").capitalize())


def majuscule(valeur):
    """Affichage seulement : première lettre en majuscule (la valeur envoyée au modèle ne change pas)."""
    texte = str(valeur)
    return texte[:1].upper() + texte[1:]


def afficher_champ(colonne, champ):
    """Affiche le widget d'un champ et renvoie la valeur saisie (None tant que rien n'est saisi)."""
    # key=colonne : permet de préremplir le champ via st.session_state (bouton de test)
    if champ["type"] == "choix":
        return st.selectbox(libelle(colonne), champ["choix"], index=None, placeholder="Choisir une valeur",
                            key=colonne, format_func=majuscule)
    return st.number_input(libelle(colonne), min_value=champ["min"], max_value=champ["max"], value=None,
                           step=1.0, format="%.0f" if colonne in CHAMPS_ENTIERS else "%.1f",
                           placeholder=f"entre {champ['min']:g} et {champ['max']:g}", key=colonne)


# TODO à supprimer : bouton de test qui remplit le formulaire avec des données fictives
def remplir_test(champs):
    """Met une valeur fictive dans chaque champ : 1re valeur des listes, minimum des nombres sauf exceptions."""
    valeurs = {"surface_habitable_logement": 60.0, "annee_construction": 1975.0, "numero_etage_appartement": 2.0}
    for colonne, champ in champs.items():
        if champ["type"] == "choix":
            st.session_state[colonne] = champ["choix"][0]
        else:
            st.session_state[colonne] = valeurs.get(colonne, champ["min"])


def afficher_precision(tache, departement):
    """Mesures du modèle sur le jeu de test, à côté d'une référence naïve (une réponse « sans modèle »)."""
    scores = service.evaluation_modele(tache, departement, "scores")
    lignes = []
    for _, ligne in scores.iterrows():
        unite = f" {ligne['unite']}" if isinstance(ligne["unite"], str) and ligne["unite"] else ""
        texte = f"- {ligne['libelle']} : **{ligne['valeur']:.2f}{unite}**"
        if pd.notna(ligne["reference_naive"]):
            texte += f" (référence naïve : {ligne['reference_naive']:.2f}{unite})"
        lignes.append(texte)
    st.markdown(f"**{TITRES_TACHES[tache]}**")
    st.markdown("\n".join(lignes))


gauche, droite = st.columns([3, 2])

with gauche:
    # hors du formulaire : changer ces choix met à jour les champs tout de suite
    bande = st.container(border=True, horizontal=True, vertical_alignment="center", key="bande_estimation")
    choix = bande.radio("Estimer", list(ESTIMATIONS), horizontal=True)
    taches = ESTIMATIONS[choix]
    # seulement les départements qui ont un modèle pour chaque tâche demandée
    departements = sorted(set.intersection(*(set(formulaire[t]) for t in taches)))
    if not departements:
        st.warning("Aucun département n'a de modèle pour cette estimation.")
        st.stop()
    departement = bande.selectbox("Département", departements, format_func=nom_departement)
    champs = champs_des_modeles(taches, departement)

    # TODO à supprimer avec remplir_test
    bande.button("Test : remplir avec des données fictives", on_click=remplir_test, args=(champs,))

    with st.form("formulaire_logement"):
        # une carte par groupe ; les champs que les groupes ne connaissent pas vont dans « Autres »
        groupes = [(titre, icone, [c for c in colonnes if c in champs]) for titre, icone, colonnes in GROUPES_CHAMPS]
        connus = {c for _, _, colonnes in GROUPES_CHAMPS for c in colonnes}
        autres = [c for c in champs if c not in connus]
        if autres:
            groupes.append(("Autres caractéristiques", "more_horiz", autres))

        valeurs = {}
        for numero, (titre, icone, colonnes) in enumerate(groupes):
            if not colonnes:
                continue
            with st.container(key=f"groupe_{numero}"):
                st.markdown(f"**:material/{icone}: {titre}**")
                deux_colonnes = st.columns(2)
                for rang, colonne in enumerate(colonnes):
                    with deux_colonnes[rang % 2]:
                        valeurs[colonne] = afficher_champ(colonne, champs[colonne])
        envoye = st.form_submit_button("Estimer ce logement", type="primary", icon=":material/calculate:")

    # même ordre de colonnes que celui des modèles (le regroupement par cartes l'a changé à l'écran)
    saisies = {colonne: valeurs[colonne] for colonne in champs}

with droite:
    with st.container(key="panneau_droit"):
        with st.container(key="panneau_resultat"):
            st.subheader(":material/insights: Résultat")
            if not envoye:
                if "classification" in taches:
                    st.markdown(echelle_dpe(), unsafe_allow_html=True)
                st.caption("Remplissez le formulaire puis cliquez sur « Estimer ce logement ».")
            else:
                # un champ numérique vide ferait passer sa colonne en texte : la prédiction serait fausse sans erreur
                manquants = [colonne for colonne, valeur in saisies.items() if valeur is None]
                if manquants:
                    st.warning("Champs à remplir : " + ", ".join(libelle(c) for c in manquants))
                else:
                    X = pd.DataFrame([saisies])
                    if "classification" in taches:
                        etiquette = str(service.predire("classification", departement, X)[0])
                        st.markdown(echelle_dpe(etiquette), unsafe_allow_html=True)
                    if "regression" in taches:
                        conso = service.predire("regression", departement, X)[0]
                        st.metric("Consommation estimée", f"{conso:.0f} kWh/m²/an")
                        st.caption("Énergie finale, par m² et par an.")
                    st.caption(
                        "Estimation d'un modèle entraîné sur les logements du département : c'est un ordre de grandeur, "
                        "pas un diagnostic officiel. Les logements très énergivores (étiquettes F et G) sont "
                        "les plus difficiles à repérer."
                    )
                    with st.expander("Voir les mesures du modèle"):
                        for tache in taches:
                            afficher_precision(tache, departement)

        with st.container(key="bloc_modeles"):
            st.subheader(":material/model_training: Modèles")
            st.write("Relancer l'apprentissage utilise les données les plus récentes et peut prendre quelques minutes.")
            if st.button("Relancer l'apprentissage", icon=":material/refresh:"):
                st.info("L'apprentissage sera disponible quand les modèles seront branchés sur l'application.")