"""Page « Prédiction » : formulaire de saisie d'un logement.

Page de saisie uniquement : le calcul de l'estimation et l'apprentissage seront branchés
plus tard, quand les modèles de l'équipe seront prêts.
"""

import streamlit as st

from lecture import charger_ou_arreter

st.title(":material/online_prediction: Prédiction")
st.write("Décrivez un logement pour estimer son étiquette DPE et sa consommation.")

donnees, meta = charger_ou_arreter()

# Les choix proposés sont les valeurs présentes dans les données
CHAMPS_CHOIX = {
    "periode_construction": "Période de construction",
    "type_batiment": "Type de bâtiment",
    "type_energie_principale_chauffage": "Énergie principale de chauffage",
    "type_installation_chauffage": "Installation de chauffage",
    "type_installation_ecs": "Installation d'eau chaude",
    "qualite_isolation_enveloppe": "Isolation de l'enveloppe",
    "qualite_isolation_murs": "Isolation des murs",
    "qualite_isolation_menuiseries": "Isolation des menuiseries",
    "qualite_isolation_plancher_bas": "Isolation du plancher bas",
    "origine": "Origine du logement",
}

gauche, droite = st.columns([3, 2])

with gauche:
    with st.form("formulaire_logement"):
        st.subheader(":material/apartment: Caractéristiques du logement")
        st.number_input("Surface habitable (m²)", 5.0, 500.0, 60.0)
        st.number_input("Hauteur sous plafond (m)", 1.5, 6.0, 2.5, step=0.1)
        for colonne, libelle in CHAMPS_CHOIX.items():
            st.selectbox(libelle, sorted(donnees[colonne].dropna().unique()))
        envoye = st.form_submit_button("Estimer ce logement", icon=":material/calculate:")

with droite:
    st.subheader(":material/insights: Résultat")
    if envoye:
        st.info("L'estimation sera disponible quand les modèles seront branchés sur l'application.")
    else:
        st.caption("Remplissez le formulaire puis cliquez sur « Estimer ce logement ».")

    st.subheader(":material/model_training: Modèles")
    st.write("Relancer l'apprentissage utilise les données les plus récentes et peut prendre quelques minutes.")
    if st.button("Relancer l'apprentissage", icon=":material/refresh:"):
        st.info("L'apprentissage sera disponible quand les modèles seront branchés sur l'application.")
