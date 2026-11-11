import requests
import streamlit as st

from src.data.api_client import AdemeApiClient
from src.orchestration.workflow_github import WorkflowGitHub, mot_de_passe_valide

# Id de la dernière exécution connue au moment du lancement : tant qu'il ne change pas, GitHub n'a pas encore créé la nouvelle
CLE_RUN_AVANT = "run_avant_reentrainement"


@st.cache_data(ttl=15, show_spinner=False)
def lire_dernier_run():
    """Dernière exécution du workflow (mise en cache pour ne pas appeler GitHub à chaque clic sur la page)."""
    return WorkflowGitHub.depuis_environnement().dernier_run()


@st.cache_data(ttl=600, show_spinner=False)
def lire_derniere_publication():
    """Date de la dernière publication de l'ADEME (mise en cache 10 minutes)."""
    return AdemeApiClient().derniere_publication()


def en_cours(run):
    """Vrai si l'exécution vient d'être demandée ou n'est pas terminée."""
    id_run = run["id"] if run else None
    if CLE_RUN_AVANT in st.session_state and st.session_state[CLE_RUN_AVANT] == id_run:
        return True
    return run is not None and run["statut"] != "completed"


@st.fragment(run_every="15s")
def suivre():
    """Affiche l'attente et recharge la page quand GitHub a terminé."""
    try:
        if not en_cours(lire_dernier_run()):
            st.rerun()
    except requests.RequestException:
        st.warning("GitHub est injoignable, nouvel essai dans quelques secondes.")
        return
    st.info("Traitement en cours sur GitHub (15 à 25 minutes pour un apprentissage seul, davantage avec un "
            "téléchargement). Vous pouvez quitter cette page.",
            icon=":material/hourglass_top:")


def afficher_dernier_resultat(run, version):
    """Résultat de la dernière exécution terminée, comparé à la version de modèles en service."""
    if run is None:
        return
    if run["conclusion"] != "success":
        st.error(f"Le dernier apprentissage n'a pas abouti. [Voir les logs]({run['url']})")
    elif version >= run["cree_le"]:
        st.success("Les modèles en service sont à jour.")


def date_fr(identifiant):
    """« 2026-11-08_165211 » devient « 08/11/2026 »."""
    return "/".join(reversed(identifiant[:10].split("-")))


def lancer(workflow, run, rafraichir=False):
    """Lance le workflow (rafraichir : avec un nouveau téléchargement) et mémorise l'exécution précédente."""
    try:
        workflow.lancer(rafraichir)
    except requests.RequestException:
        st.error("GitHub a refusé le lancement : vérifiez GITHUB_TOKEN, GITHUB_DEPOT et GITHUB_BRANCHE.")
        return
    st.session_state[CLE_RUN_AVANT] = run["id"] if run else None
    st.rerun()


def afficher_bloc_reentrainement(meta):
    """Date des modèles en service (meta : meta.json d'un modèle), puis formulaire protégé par mot de passe,
    ou suivi si un apprentissage est en cours."""
    version = meta["snapshot_id"]
    donnees = meta.get("snapshot_source", version)
    st.write(f"Modèles en service entraînés le **{date_fr(version)}** "
             f"sur les données téléchargées le **{date_fr(donnees)}**.")
    workflow = WorkflowGitHub.depuis_environnement()
    if workflow is None:
        st.caption("Apprentissage non configuré : GITHUB_DEPOT, GITHUB_TOKEN et MOT_DE_PASSE_ADMIN sont requis.")
        return
    try:
        run = lire_dernier_run()
    except requests.RequestException:
        st.warning("Impossible de joindre GitHub : vérifiez GITHUB_TOKEN, GITHUB_DEPOT et GITHUB_BRANCHE.")
        return
    if en_cours(run):
        suivre()
        return
    afficher_dernier_resultat(run, version)
    with st.form("formulaire_reentrainement", border=False, clear_on_submit=True):
        saisi = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Relancer l'apprentissage", icon=":material/refresh:"):
            if mot_de_passe_valide(saisi):
                lancer(workflow, run)
            else:
                st.error("Mot de passe incorrect.")


def afficher_bloc_rafraichissement(snapshot):
    """Page Contexte : formulaire protégé par mot de passe qui lance toute la pipeline sur un nouveau
    téléchargement, ou suivi si un traitement est en cours. snapshot : id du snapshot de données affiché."""
    workflow = WorkflowGitHub.depuis_environnement()
    if workflow is None:
        st.caption("Rafraîchissement non configuré : GITHUB_DEPOT, GITHUB_TOKEN et MOT_DE_PASSE_ADMIN sont requis.")
        return
    try:
        run = lire_dernier_run()
    except requests.RequestException:
        st.warning("Impossible de joindre GitHub : vérifiez GITHUB_TOKEN, GITHUB_DEPOT et GITHUB_BRANCHE.")
        return
    if en_cours(run):
        suivre()
        return
    if run is not None and run["conclusion"] != "success":
        st.error(f"Le dernier traitement n'a pas abouti. [Voir les logs]({run['url']})")
    elif run is not None and snapshot >= run["cree_le"]:
        st.success("Les données affichées viennent du dernier rafraîchissement.")
    # l'ADEME a-t-elle publié depuis le téléchargement affiché ? (l'id du snapshot est sa date de téléchargement)
    try:
        publication = lire_derniere_publication()
    except requests.RequestException:
        st.warning("ADEME injoignable : impossible de savoir si de nouvelles données ont été publiées.")
        publication = None
    a_jour = publication is not None and publication <= snapshot
    if a_jour:
        st.info(f"Données à jour : dernière publication de l'ADEME le {date_fr(publication)}, "
                f"téléchargement le {date_fr(snapshot)}.")
    elif publication is not None:
        st.info(f"Nouvelle publication de l'ADEME le {date_fr(publication)}, "
                f"données affichées téléchargées le {date_fr(snapshot)}.")
    with st.form("formulaire_rafraichissement", border=False, clear_on_submit=True):
        # sans nouvelle publication, le téléchargement doit être demandé explicitement
        forcer = st.checkbox("Retélécharger quand même") if a_jour else True
        saisi = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Rafraîchir les données", icon=":material/refresh:"):
            if not forcer:
                st.error("Aucune nouvelle publication : cochez « Retélécharger quand même » pour relancer.")
            elif mot_de_passe_valide(saisi):
                lancer(workflow, run, rafraichir=True)
            else:
                st.error("Mot de passe incorrect.")
