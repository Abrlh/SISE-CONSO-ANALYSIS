import requests
import streamlit as st

from src.orchestration.workflow_github import WorkflowGitHub, mot_de_passe_valide

# Id de la dernière exécution connue au moment du lancement : tant qu'il ne change pas, GitHub n'a pas encore créé la nouvelle
CLE_RUN_AVANT = "run_avant_reentrainement"


@st.cache_data(ttl=15, show_spinner=False)
def lire_dernier_run():
    """Dernière exécution du workflow (mise en cache pour ne pas appeler GitHub à chaque clic sur la page)."""
    return WorkflowGitHub.depuis_environnement().dernier_run()


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
    st.info("Apprentissage en cours sur GitHub (environ 15 à 25 minutes). Vous pouvez quitter cette page.",
            icon=":material/hourglass_top:")


def afficher_dernier_resultat(run, version):
    """Résultat de la dernière exécution terminée, comparé à la version de modèles en service."""
    if run is None:
        return
    if run["conclusion"] != "success":
        st.error(f"Le dernier apprentissage n'a pas abouti. [Voir les logs]({run['url']})")
    elif version >= run["cree_le"]:
        st.success("Les modèles en service sont à jour.")
    else:
        st.info("Nouveaux modèles publiés : ils seront utilisés au prochain redéploiement. "
                "En local : `git pull` puis relancer l'application.")


def lancer(workflow, run):
    """Lance le workflow et mémorise l'exécution précédente."""
    try:
        workflow.lancer()
    except requests.RequestException:
        st.error("GitHub a refusé le lancement : vérifiez GITHUB_TOKEN, GITHUB_DEPOT et GITHUB_BRANCHE.")
        return
    st.session_state[CLE_RUN_AVANT] = run["id"] if run else None
    st.rerun()


def afficher_bloc_reentrainement(version):
    """Formulaire protégé par mot de passe, ou suivi si un apprentissage est en cours."""
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
