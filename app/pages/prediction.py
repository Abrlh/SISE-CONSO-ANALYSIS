"""Page « Prédiction » : formulaire de saisie d'un logement et estimation.

Les champs du formulaire et leurs choix viennent des modèles entraînés (AppService.formulaire),
l'estimation de AppService.predire. Le réentraînement est dans app/reentrainement.py.
"""

import pandas as pd
import streamlit as st

from affichage import (
    CHAMPS_ENTIERS, DESCRIPTIONS_GROUPES, GROUPES_CHAMPS, NOMS_CHAMPS, NOMS_DEPARTEMENTS, nom_departement,
)
from deps import get_service
from reentrainement import afficher_bloc_reentrainement
from style import echelle_dpe, habiller_prediction, jauge_fiabilite, tuile_resultat

st.title(":material/online_prediction: Prédiction")
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
    valeurs = {"surface_habitable_logement": 60.0, "annee_construction": 1975.0}
    for colonne, champ in champs.items():
        if champ["type"] == "choix":
            st.session_state[colonne] = champ["choix"][0]
        else:
            st.session_state[colonne] = valeurs.get(colonne, champ["min"])


def afficher_precision(tache, departement):
    """Mesures du modèle sur le jeu de test, à côté de la référence naïve."""
    scores = service.evaluation_modele(tache, departement, "scores")
    lignes = []
    for _, ligne in scores.iterrows():
        unite = f" {ligne['unite']}" if isinstance(ligne["unite"], str) and ligne["unite"] else ""
        reference = f"{ligne['reference_naive']:.2f}{unite}" if pd.notna(ligne["reference_naive"]) else "—"
        lignes.append({"Mesure": ligne["libelle"], "Modèle": f"{ligne['valeur']:.2f}{unite}", "Référence naïve": reference})
    if len(taches) > 1:
        st.markdown(f"**{TITRES_TACHES[tache]}**")
    st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")


def fiabilite_etiquette(departement):
    """Part des étiquettes devinées exactement sur le jeu de test (en %), lue dans les scores du modèle.
    Renvoie None si le tableau ne contient pas cette mesure."""
    try:
        scores = service.evaluation_modele("classification", departement, "scores")
    except (FileNotFoundError, KeyError, ValueError):
        return None
    for _, ligne in scores.iterrows():
        nom = f"{ligne['metrique']} {ligne['libelle']}".lower()
        if "exact" in nom or "accuracy" in nom:
            valeur = float(ligne["valeur"])
            return valeur * 100 if valeur <= 1 else valeur
    return None


gauche, droite = st.columns([6, 5])

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

    # une étape par groupe ; les champs que les groupes ne connaissent pas vont dans « Autres caractéristiques »
    groupes = [(titre, icone, [c for c in colonnes if c in champs]) for titre, icone, colonnes in GROUPES_CHAMPS]
    connus = {c for _, _, colonnes in GROUPES_CHAMPS for c in colonnes}
    autres = [c for c in champs if c not in connus]
    if autres:
        groupes.append(("Autres caractéristiques", "more_horiz", autres))
    groupes = [groupe for groupe in groupes if groupe[2]]
    habiller_prediction([len(colonnes) for _, _, colonnes in groupes])

    with st.form("formulaire_logement"):
        valeurs = {}
        etape_du_champ = {}
        # st.tabs dans un formulaire : tous les onglets sont envoyés ensemble au clic sur le bouton
        with st.container(key="etapes"):
            onglets = st.tabs([f":material/{icone}: {titre}" for titre, icone, _ in groupes])
            for rang_onglet, (onglet, (titre, icone, colonnes)) in enumerate(zip(onglets, groupes)):
                with onglet:
                    # en-tête de l'étape : pastille d'icône, titre et description
                    colonne_icone, colonne_texte = st.columns([1, 11], vertical_alignment="center")
                    with colonne_icone:
                        with st.container(key=f"icone_etape_{rang_onglet}"):
                            st.markdown(f":material/{icone}:")
                    colonne_texte.html(
                        f'<div class="etape-texte"><b>{titre}</b><span>{DESCRIPTIONS_GROUPES.get(titre, "")}</span></div>'
                    )
                    deux_colonnes = st.columns(2)
                    for rang, colonne in enumerate(colonnes):
                        etape_du_champ[colonne] = titre
                        with deux_colonnes[rang % 2]:
                            valeurs[colonne] = afficher_champ(colonne, champs[colonne])
        envoye = st.form_submit_button("Estimer ce logement", type="primary", icon=":material/calculate:")
        st.caption(f"Remplissez les {len(groupes)} onglets avant d'estimer.")

    # même ordre de colonnes que celui des modèles (le regroupement par cartes l'a changé à l'écran)
    saisies = {colonne: valeurs[colonne] for colonne in champs}

with droite:
    with st.container(key="panneau_droit"):
        with st.container(key="panneau_resultat"):
            st.subheader(":material/insights: Résultat")
            avec_etiquette = "classification" in taches
            avec_consommation = "regression" in taches
            if not envoye:
                st.markdown(tuile_resultat(None, None, avec_etiquette, avec_consommation), unsafe_allow_html=True)
                if avec_etiquette:
                    st.markdown(echelle_dpe(), unsafe_allow_html=True)
                st.caption("Remplissez le formulaire puis cliquez sur « Estimer ce logement ».")
            else:
                # un champ numérique vide ferait passer sa colonne en texte : la prédiction serait fausse sans erreur
                manquants = [colonne for colonne, valeur in saisies.items() if valeur is None]
                if manquants:
                    st.warning(
                        "Champs à remplir : "
                        + ", ".join(f"{libelle(c)} ({etape_du_champ[c]})" for c in manquants)
                    )
                else:
                    X = pd.DataFrame([saisies])
                    etiquette = consommation = None
                    if avec_etiquette:
                        etiquette = str(service.predire("classification", departement, X)[0])
                    if avec_consommation:
                        consommation = float(service.predire("regression", departement, X)[0])
                    st.markdown(
                        tuile_resultat(etiquette, consommation, avec_etiquette, avec_consommation),
                        unsafe_allow_html=True,
                    )
                    if avec_etiquette:
                        st.markdown(echelle_dpe(etiquette), unsafe_allow_html=True)
                        fiabilite = fiabilite_etiquette(departement)
                        if fiabilite is not None:
                            nom_court = NOMS_DEPARTEMENTS.get(departement, departement)
                            st.markdown(jauge_fiabilite(fiabilite, nom_court), unsafe_allow_html=True)
                    st.caption("Estimation indicative, pas un diagnostic officiel.")
                    with st.expander("Mesures détaillées"):
                        for tache in taches:
                            afficher_precision(tache, departement)

        with st.container(key="bloc_modeles"):
            st.subheader(":material/model_training: Modèles")
            st.write("Réentraîne les modèles sur les données actuelles, sans nouveau téléchargement.")
            afficher_bloc_reentrainement(service.info_modele(taches[0], departement))