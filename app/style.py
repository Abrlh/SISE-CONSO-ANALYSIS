"""Style de l'application : l'habillage du menu de gauche, les cartes et la bannière de l'Accueil.

Le style est du CSS (la langue des couleurs et des mises en forme du web), envoyé à Streamlit sous
forme de texte. La bannière utilise aussi du HTML (la structure) et un dessin SVG (des formes dessinées
par des coordonnées). Les couleurs viennent des étiquettes DPE de l'application. Aucun calcul ici.
"""
import math

import streamlit as st


# Couleur de la tuile d'icône de chaque page, dans l'ordre du menu.
# Ce sont des couleurs d'étiquettes DPE : A (vert), C (citron), E (jaune), F (orange).
COULEURS_PAGES = {
    "Accueil": "#319834",
    "Contexte": "#CBFC34",
    "Statistiques": "#FBCC05",
    "Prédiction": "#FC9935",
}

# Les noms entre crochets (data-testid) sont ceux que Streamlit donne aux éléments du menu
CSS_MENU = """
/* Moins d'espace vide autour du contenu : Streamlit en laisse beaucoup par défaut.
   Plusieurs noms sont listés car Streamlit nomme ce bloc différemment selon les versions. */
.block-container,
.stMainBlockContainer,
[data-testid="stMainBlockContainer"] {
    padding-top: 3rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
}
/* Titre de page : on enlève la marge que Streamlit ajoute au-dessus d'un titre */
[data-testid="stMainBlockContainer"] h1,
.block-container h1 {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
/* Les blocs de style (st.html) posés tout en haut de la page ne doivent pas laisser de vide */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(> [data-testid="stHtml"]) {
    display: none;
}
/* Le cadre de 1 pixel de empecher_traduction : on le range hors du flux de la page */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(iframe) {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
}

/* Fond du menu : dégradé du vert pâle (haut) vers le pêche (bas) */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #F1F9E4 0%, #EAF6D6 45%, #FFF1CC 80%, #FFE2B3 100%);
}
[data-testid="stSidebar"] > div:first-child {
    background: transparent;
}

/* En-tête du menu moins haut : le menu démarre à la même hauteur que la bannière */
[data-testid="stSidebarHeader"] {
    height: 1.5rem;
    min-height: 0;
    padding-bottom: 0;
}

/* Le texte de bas de menu est poussé tout en bas du menu */
[data-testid="stSidebarContent"] {
    display: flex;
    flex-direction: column;
}
[data-testid="stSidebarUserContent"] {
    margin-top: auto;
    padding-bottom: 1.2rem;
}

/* Espace entre deux pages du menu */
[data-testid="stSidebarNavItems"] {
    gap: 8px;
}

/* Chaque page du menu : une ligne haute et arrondie */
[data-testid="stSidebarNavLink"] {
    position: relative;
    height: 54px;
    padding: 0 12px;
    gap: 14px;
    border-radius: 18px;
    color: #17301B;
    font-weight: 500;
}

/* L'icône devient une tuile arrondie colorée */
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {
    position: relative;
    z-index: 1;
    width: 34px;
    height: 34px;
    min-width: 34px;
    flex: none;
    border-radius: 11px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #17301B;
}

/* Page sélectionnée : pastille blanche avec une ombre douce, texte en gras */
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: #FFFFFF;
    font-weight: 700;
    box-shadow: 0 10px 22px -14px rgba(23, 48, 27, 0.6);
}

/* Fil de couleur qui relie Contexte, Statistiques et Prédiction (comme les cartes de l'Accueil).
   Il est accroché au centre de la tuile d'icône : il reste donc toujours droit. */
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {
    overflow: visible;
}
[data-testid="stSidebarNavItems"] > li:nth-child(n+3) [data-testid="stIconMaterial"]::before {
    content: "";
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    bottom: 100%;
    width: 5px;
    height: 28px;
    border-radius: 5px;
}
[data-testid="stSidebarNavItems"] > li:nth-child(3) [data-testid="stIconMaterial"]::before {
    background: linear-gradient(180deg, #CBFC34, #FBCC05);
}
[data-testid="stSidebarNavItems"] > li:nth-child(4) [data-testid="stIconMaterial"]::before {
    background: linear-gradient(180deg, #FBCC05, #FC9935);
}
"""


def habiller_menu():
    """Donne au menu de gauche son habillage : tuiles colorées, page choisie en blanc, fil de couleur."""
    # Une règle par page pour colorer sa tuile (la page numéro 1 est la première du menu, etc.)
    regles_tuiles = ""
    for numero, couleur in enumerate(COULEURS_PAGES.values(), start=1):
        regles_tuiles += (
            f'[data-testid="stSidebarNavItems"] > li:nth-child({numero}) '
            f'[data-testid="stIconMaterial"] {{ background: {couleur}; }}\n'
        )
    # st.html (et non st.markdown) pour que ce bloc de style ne laisse pas d'espace vide en haut de page
    st.html(f"<style>{CSS_MENU}{regles_tuiles}</style>")


# CARTES DE L'ACCUEIL : trois cartes numérotées, cliquables en entier
# Pour chaque carte : (nom de la carte, couleur de fond, couleur de l'étiquette, dégradé vers la suivante)
CARTES = [
    ("carte_contexte", "#F2FCCC", "#CBFC34", "linear-gradient(90deg, #CBFC34, #FBCC05)"),
    ("carte_statistiques", "#FEF2C0", "#FBCC05", "linear-gradient(90deg, #FBCC05, #FC9935)"),
    ("carte_prediction", "#FFD9A3", "#FC9935", None),
]

CSS_CARTES = """
/* Toutes les cartes : même forme, même hauteur minimale */
[class*="st-key-carte_"] {
    position: relative;
    gap: 0.5rem;
    min-height: 176px;
    margin-top: 22px;
    padding: 28px 20px 18px;
    border-radius: 24px;
    box-shadow: 0 14px 26px -22px rgba(15, 61, 58, 0.7);
}
/* Streamlit rapproche ses blocs de texte avec des marges négatives : on les remet à zéro ici */
[class*="st-key-carte_"] [data-testid="stElementContainer"],
[class*="st-key-carte_"] [data-testid="stMarkdown"],
[class*="st-key-carte_"] [data-testid="stMarkdownContainer"] {
    margin-bottom: 0;
}

/* Le lien « Ouvrir … » reste en bas de chaque carte, à la même hauteur */
[class*="st-key-carte_"] > [data-testid="stElementContainer"]:last-child {
    margin-top: auto;
}
/* Les textes de la carte */
[class*="st-key-carte_"] [data-testid="stMarkdownContainer"] p {
    margin: 0;
    font-size: 13.5px;
    line-height: 1.5;
    color: #4D6150;
}
[class*="st-key-carte_"] [data-testid="stMarkdownContainer"] strong {
    font-size: 17px;
    color: #17301B;
}
/* Le lien « Ouvrir... » : souligné, vert foncé */
[class*="st-key-carte_"] a {
    position: static;
    padding: 0;
    background: transparent;
    color: #1F6B26;
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 4px;
}
/* Astuce : une zone invisible, étirée sur toute la carte, fait de la carte entière un lien */
[class*="st-key-carte_"] a::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 24px;
}
[class*="st-key-carte_"] a:focus-visible::after {
    outline: 3px solid #319834;
    outline-offset: 2px;
}
/* Léger soulèvement au survol, seulement si l'utilisateur n'a pas demandé moins d'animations */
@media (prefers-reduced-motion: no-preference) {
    [class*="st-key-carte_"] { transition: transform 0.15s ease, box-shadow 0.15s ease; }
    [class*="st-key-carte_"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 18px 28px -20px rgba(15, 61, 58, 0.75);
    }
}
/* Le numéro de l'étape, posé sur le bord haut de la carte */
[class*="st-key-carte_"]::before {
    position: absolute;
    left: 20px;
    top: -17px;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    font-weight: 700;
    font-size: 15px;
    color: #17301B;
    box-shadow: 0 4px 0 rgba(0, 0, 0, 0.14);
}
"""


def habiller_cartes():
    """Donne aux trois cartes de l'Accueil leurs couleurs, leurs numéros et les traits qui les relient."""
    regles = ""
    for numero, (nom, fond, couleur, degrade) in enumerate(CARTES, start=1):
        regles += (
            f".st-key-{nom} {{ background: {fond}; border-bottom: 5px solid {couleur}; }}\n"
            f'.st-key-{nom}::before {{ content: "{numero}"; background: {couleur}; }}\n'
        )
        if degrade:
            # Trait entre cette carte et la suivante (l'espace entre deux cartes fait 16 px)
            regles += (
                f'.st-key-{nom}::after {{ content: ""; position: absolute; top: -2px; left: 54px; '
                f"width: calc(100% - 18px); height: 4px; border-radius: 4px; background: {degrade}; }}\n"
            )
    st.html(f"<style>{CSS_CARTES}{regles}</style>")


def pied_de_menu():
    """Affiche en bas du menu de gauche la source des données et le nom du projet."""
    with st.sidebar:
        st.markdown(
            '<div style="font-size:12px;line-height:1.5;color:#4D6150">'
            "Source des données : ADEME, DPE des logements existants et neufs."
            "<br><br>Projet M2 SISE </div>",
            unsafe_allow_html=True,
        )


def empecher_traduction():
    """Indique au navigateur que la page est en français et qu'il ne doit pas la traduire.

    Sans cela, la traduction automatique d'un téléphone réécrit les textes et fait planter l'affichage.
    """
    st.iframe(
        """
        <script>
        const doc = window.parent.document;
        doc.documentElement.lang = "fr";
        doc.documentElement.setAttribute("translate", "no");
        if (!doc.querySelector('meta[name="google"]')) {
            const meta = doc.createElement("meta");
            meta.name = "google";
            meta.content = "notranslate";
            doc.head.appendChild(meta);
        }
        </script>
        """,
        height=1,
    )


# BANNIÈRE DE L'ACCUEIL : mise en forme (CSS). Les noms commencent par « dpe- » pour ne pas se
# mélanger à ceux de Streamlit.

CSS_BANNIERE = """
.dpe-banniere {
    position: relative;
    overflow: hidden;
    box-sizing: border-box;
    padding: 28px 46px 46px;
    border-radius: 32px;
    background: linear-gradient(100deg, #DDF2D3 0%, #EAF8C6 30%, #FFF6B8 55%, #FFE09E 78%, #FFC77F 100%);
    box-shadow: 0 30px 50px -36px rgba(15, 61, 58, 0.55);
    color: #17301B;
    container-type: inline-size;
}
/* Le soleil */
.dpe-banniere::before {
    content: "";
    position: absolute;
    right: 58px;
    top: 26px;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: #FBCC05;
    box-shadow: 0 0 0 14px rgba(251, 204, 5, 0.28), 0 0 0 32px rgba(251, 204, 5, 0.14);
}
/* La bande des sept couleurs d'étiquettes, A à G, tout en bas */
.dpe-banniere::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 12px;
    background: linear-gradient(90deg, #319834 0 14.28%, #33CC31 0 28.57%, #CBFC34 0 42.85%,
        #FBFE06 0 57.14%, #FBCC05 0 71.42%, #FC9935 0 85.7%, #FC0205 0);
}
.dpe-texte {
    position: relative;
    z-index: 2;
    max-width: min(480px, 54cqw);
}
.dpe-pastille {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 99px;
    background: #FFFFFF;
    font-size: 12.5px;
    font-weight: 500;
    box-shadow: 0 8px 16px -10px rgba(15, 61, 58, 0.6);
}
.dpe-pastille i {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #FC9935;
}
.dpe-titre {
    margin: 14px 0 10px;
    font-size: clamp(24px, 3.5cqw, 31px);
    font-weight: 700;
    line-height: 1.12;
    letter-spacing: -0.03em;
}
.dpe-paragraphe {
    max-width: min(440px, 52cqw);
    margin: 0 0 18px;
    font-size: 13.5px;
    line-height: 1.5;
    color: #46604A;
}
/* Les sept pastilles A à G dans un cadre blanc translucide */
.dpe-echelle {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    width: max-content;
    max-width: 100%;
    padding: 8px 10px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.72);
    box-shadow: 0 12px 22px -16px rgba(23, 48, 27, 0.55);
}
.dpe-echelle i {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    font-style: normal;
    font-size: 13px;
    font-weight: 700;
    box-shadow: 0 3px 0 rgba(0, 0, 0, 0.14);
}
/* Le dessin, à droite */
.dpe-scene {
    position: absolute;
    right: -26px;
    top: 4px;
    z-index: 1;
    width: clamp(440px, 64cqw, 660px);
}
/* Les nuages */
.dpe-nuage {
    position: absolute;
    z-index: 0;
    height: 34px;
    border-radius: 99px;
    background: #FFFFFF;
    opacity: 0.8;
}
.dpe-nuage::before, .dpe-nuage::after {
    content: "";
    position: absolute;
    border-radius: 50%;
    background: #FFFFFF;
}
.dpe-nuage::before { width: 46px; height: 46px; left: 22%; top: -22px; }
.dpe-nuage::after { width: 62px; height: 62px; left: 48%; top: -32px; }
/* Bannière étroite : on retire le dessin et les nuages pour que rien ne se chevauche */
@container (max-width: 744px) {
    .dpe-scene, .dpe-nuage { display: none; }
}
/* Écran étroit (téléphone) : on retire le soleil et on réduit les textes */
@media (max-width: 900px) {
    .dpe-banniere::before { display: none; }
    .dpe-banniere { padding: 28px 22px 48px; border-radius: 28px; }
    .dpe-titre { font-size: 28px; }
    .dpe-echelle { gap: 5px; padding: 8px 10px; }
    .dpe-echelle i { width: 32px; height: 32px; font-size: 14px; }
}
"""

# Le dessin (SVG) : un logement existant, un logement neuf, une éolienne, un poteau électrique
# et une borne de recharge. Chaque ligne est une forme.
SCENE_SVG = """<svg viewBox="-30 -40 760 560" width="100%" style="display:block" role="img" aria-label="Illustration : un logement existant et un logement neuf, avec éolienne, poteau électrique et borne de recharge">
<ellipse cx="352" cy="310" rx="200" ry="58" fill="#17301B" opacity=".13"/>
<polygon points="300.0,150.0 546.8,292.5 403.9,375.0 157.1,232.5" fill="#BDE8A3" />
<polygon points="157.1,250.5 403.9,393.0 403.9,375.0 157.1,232.5" fill="#8ED07A" />
<polygon points="546.8,310.5 403.9,393.0 403.9,375.0 546.8,292.5" fill="#6FB85E" />
<polygon points="211.7,263.7 229.9,274.2 266.2,253.2 248.0,242.7" fill="#EFE3C8" />
<polygon points="316.9,324.4 335.1,334.9 371.4,313.9 353.3,303.4" fill="#EFE3C8" />
<ellipse cx="502.6" cy="291" rx="11" ry="5" fill="#E8EEF0"/>
<polygon points="500.1,78 505.1,78 507.1,291 498.1,291" fill="#fff" stroke="#B3C4CB" stroke-width="1.2"/>
<path d="M508.0 79.0 Q511.6 50.1 512.7 20.9 Q504.7 48.9 497.2 77.0z" fill="#fff" stroke="#B3C4CB" stroke-width="1.3" stroke-linejoin="round"/>
<path d="M499.1 82.2 Q522.2 99.7 547.0 115.3 Q526.7 94.3 506.1 73.8z" fill="#fff" stroke="#B3C4CB" stroke-width="1.3" stroke-linejoin="round"/>
<path d="M500.7 72.8 Q474.0 84.2 448.1 97.8 Q476.4 90.7 504.5 83.2z" fill="#fff" stroke="#B3C4CB" stroke-width="1.3" stroke-linejoin="round"/>
<circle cx="502.6" cy="78" r="7" fill="#fff" stroke="#B3C4CB" stroke-width="1.4"/>
<polygon points="196.1,224.6 302.6,286.1 283.1,297.3 176.6,235.8" fill="#1F5A2A" opacity=".16"/>
<polygon points="331.2,296.6 424.7,350.6 401.3,364.1 307.8,310.1" fill="#1F5A2A" opacity=".16"/>
<polygon points="388.3,234.0 300.0,285.0 300.0,207.0 388.3,156.0" fill="#E4D8C8" />
<polygon points="196.1,225.0 300.0,285.0 300.0,207.0 196.1,147.0" fill="#FBF3E6" />
<polygon points="388.3,156.0 300.0,207.0 344.2,130.5" fill="#E4D8C8" />
<polygon points="206.5,195.0 228.6,207.8 228.6,180.8 206.5,168.0" fill="#CFEAFB" stroke="#fff" stroke-width="2"/>
<polygon points="263.6,228.0 285.7,240.8 285.7,213.8 263.6,201.0" fill="#CFEAFB" stroke="#fff" stroke-width="2"/>
<polygon points="235.1,247.5 253.2,258.0 253.2,214.5 235.1,204.0" fill="#8B5E3C" />
<polygon points="370.1,214.5 350.7,225.8 350.7,195.8 370.1,184.5" fill="#BFDDF0" stroke="#fff" stroke-width="2"/>
<polygon points="331.2,237.0 311.7,248.2 311.7,218.2 331.2,207.0" fill="#BFDDF0" stroke="#fff" stroke-width="2"/>
<polygon points="179.2,152.2 298.7,221.2 352.0,135.0 232.5,66.0" fill="#D9533F" />
<line x1="192.5" y1="130.7" x2="312.0" y2="199.7" stroke="#B93F2D" stroke-width="2"/>
<line x1="205.8" y1="109.1" x2="325.3" y2="178.1" stroke="#B93F2D" stroke-width="2"/>
<line x1="219.1" y1="87.6" x2="338.6" y2="156.6" stroke="#B93F2D" stroke-width="2"/>
<polygon points="332.5,140.2 319.5,147.8 319.5,110.2 332.5,102.8" fill="#9A6558" />
<polygon points="306.5,140.2 319.5,147.8 319.5,110.2 306.5,102.8" fill="#B5776A" />
<polygon points="319.5,95.2 332.5,102.8 319.5,110.2 306.5,102.8" fill="#8A5A4B" />
<polygon points="500.0,304.5 422.1,349.5 422.1,247.5 500.0,202.5" fill="#DCE9EE" />
<polygon points="331.2,297.0 422.1,349.5 422.1,247.5 331.2,195.0" fill="#FFFFFF" />
<polygon points="409.1,150.0 500.0,202.5 422.1,247.5 331.2,195.0" fill="#FFFFFF" />
<polygon points="507.8,202.5 422.1,252.0 422.1,243.8 507.8,194.2" fill="#4C9A3E" />
<polygon points="323.4,195.0 422.1,252.0 422.1,243.8 323.4,186.8" fill="#5FAE4E" />
<polygon points="409.1,137.2 507.8,194.2 422.1,243.8 323.4,186.8" fill="#7FCB6A" />
<polygon points="331.2,247.5 422.1,300.0 422.1,294.0 331.2,241.5" fill="#C99764" />
<polygon points="339.0,288.0 370.1,306.0 370.1,274.5 339.0,256.5" fill="#9ED3F2" stroke="#fff" stroke-width="2"/>
<polygon points="339.0,240.0 370.1,258.0 370.1,228.0 339.0,210.0" fill="#9ED3F2" stroke="#fff" stroke-width="2"/>
<polygon points="376.6,309.8 414.3,331.5 414.3,300.0 376.6,278.2" fill="#9ED3F2" stroke="#fff" stroke-width="2"/>
<polygon points="376.6,261.8 414.3,283.5 414.3,253.5 376.6,231.8" fill="#9ED3F2" stroke="#fff" stroke-width="2"/>
<polygon points="489.7,295.5 466.3,309.0 466.3,240.0 489.7,226.5" fill="#8BC6EA" stroke="#fff" stroke-width="2"/>
<polygon points="453.3,316.5 429.9,330.0 429.9,261.0 453.3,247.5" fill="#8BC6EA" stroke="#fff" stroke-width="2"/>
<polygon points="409.1,149.7 431.2,162.4 379.2,192.4 357.2,179.7" fill="#2B4C9B" stroke="#7FA2E8" stroke-width="1.2"/>
<polygon points="435.1,164.7 457.2,177.4 405.2,207.4 383.1,194.7" fill="#2B4C9B" stroke="#7FA2E8" stroke-width="1.2"/>
<polygon points="461.1,179.7 483.2,192.4 431.2,222.4 409.1,209.7" fill="#2B4C9B" stroke="#7FA2E8" stroke-width="1.2"/>
<ellipse cx="163.6" cy="228.8" rx="18" ry="6" fill="#000" opacity=".12"/>
<rect x="160.6" y="199.8" width="6" height="28" fill="#7A5A3A"/>
<circle cx="163.6" cy="179.8" r="24" fill="#3F9E5A"/>
<circle cx="151.6" cy="191.8" r="16" fill="#58B66E"/>
<circle cx="174.6" cy="173.8" r="14" fill="#2F8C4C"/>
<ellipse cx="401.3" cy="367.5" rx="15" ry="5" fill="#000" opacity=".12"/>
<rect x="398.3" y="342.4" width="6" height="24" fill="#7A5A3A"/>
<circle cx="401.3" cy="325.4" r="20" fill="#3F9E5A"/>
<circle cx="391.1" cy="335.6" r="14" fill="#58B66E"/>
<circle cx="410.7" cy="320.3" r="12" fill="#2F8C4C"/>
<ellipse cx="290.9" cy="306.8" rx="11" ry="4" fill="#000" opacity=".12"/>
<rect x="287.9" y="288.1" width="6" height="17" fill="#7A5A3A"/>
<circle cx="290.9" cy="276.1" r="14" fill="#3F9E5A"/>
<circle cx="283.7" cy="283.4" r="10" fill="#58B66E"/>
<circle cx="297.5" cy="272.6" r="8" fill="#2F8C4C"/>
<ellipse cx="604" cy="318" rx="20" ry="6" fill="#17301B" opacity=".16"/>
<line x1="604" y1="316" x2="604" y2="112" stroke="#6B4A2B" stroke-width="8" stroke-linecap="round"/>
<line x1="574" y1="128" x2="634" y2="146" stroke="#4A3620" stroke-width="6" stroke-linecap="round"/>
<line x1="582" y1="156" x2="626" y2="169" stroke="#4A3620" stroke-width="5" stroke-linecap="round"/>
<rect x="592" y="176" width="24" height="34" rx="6" fill="#9AA7AD" stroke="#fff" stroke-width="2"/>
<rect x="592" y="176" width="24" height="9" rx="4" fill="#C5D0D5"/>
<path d="M606 190 l-6 10 h5 l-2 8 8 -12 h-5 z" fill="#FBCC05"/>
<circle cx="574" cy="124" r="4" fill="#CFEAFB" stroke="#fff" stroke-width="1.5"/>
<circle cx="634" cy="142" r="4" fill="#CFEAFB" stroke="#fff" stroke-width="1.5"/>
<path d="M574 124 Q540 200 497 214" fill="none" stroke="#17301B" stroke-width="2.6"/>
<path d="M634 142 Q690 150 740 126" fill="none" stroke="#17301B" stroke-width="2.6"/>
<path d="M574 124 Q500 112 440 132" fill="none" stroke="#17301B" stroke-width="2.6" opacity="0"/>
<ellipse cx="520" cy="312" rx="14" ry="5" fill="#17301B" opacity=".18"/>
<polygon points="536,310 520,319 520,262 536,253" fill="#DCE9EE"/>
<polygon points="504,310 520,319 520,262 504,253" fill="#FFFFFF" stroke="#D5DEE2"/>
<polygon points="520,247 536,253 520,262 504,253" fill="#F6FFF4"/>
<polygon points="509,285 516,289 516,271 509,267" fill="#33CC31"/>
<path d="M510 276 l6 3.5 l-4 -8 l6 3.5" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" opacity="0"/>
<path d="M504 296 C486 300 482 318 498 322" fill="none" stroke="#17301B" stroke-width="2.4" stroke-linecap="round"/>
<circle cx="498" cy="322" r="3.2" fill="#33CC31" stroke="#17301B" stroke-width="1.2"/>
<line x1="292" y1="74" x2="292" y2="108" stroke="#17301B" stroke-width="2" stroke-dasharray="3 4"/>
<g transform="translate(258 40)">
<rect x="-29.0" y="-8" width="132" height="26" rx="13" fill="#fff"/>
<text x="37" y="10" text-anchor="middle" font-family="Poppins" font-weight="600" font-size="12.5" fill="#17301B">Logement existant</text>
</g>
<line x1="416" y1="152" x2="416" y2="186" stroke="#17301B" stroke-width="2" stroke-dasharray="3 4"/>
<g transform="translate(382 118)">
<rect x="-17.0" y="-8" width="108" height="26" rx="13" fill="#fff"/>
<text x="37" y="10" text-anchor="middle" font-family="Poppins" font-weight="600" font-size="12.5" fill="#17301B">Logement neuf</text>
</g>
<circle cx="321" cy="88" r="5" fill="#fff" opacity=".85"/>
<circle cx="329" cy="73" r="7.5" fill="#fff" opacity=".7"/></svg>"""

# Les sept pastilles : (lettre, couleur du fond, couleur de la lettre)
ECHELLE = [
    ("A", "#319834", "#FFFFFF"),
    ("B", "#33CC31", "#17301B"),
    ("C", "#CBFC34", "#17301B"),
    ("D", "#FBFE06", "#17301B"),
    ("E", "#FBCC05", "#17301B"),
    ("F", "#FC9935", "#17301B"),
    ("G", "#FC0205", "#FFFFFF"),
]


def banniere_accueil():
    """Affiche la bannière de l'Accueil : titre, présentation, pastilles A à G et dessin."""
    pastilles = "".join(
        f'<i style="background:{fond};color:{lettre}">{nom}</i>' for nom, fond, lettre in ECHELLE
    )
    # Le HTML est écrit sans ligne vide ni retrait : sinon Streamlit le prendrait pour du texte
    html = (
        '<div class="dpe-banniere">'
        '<div class="dpe-nuage" style="right:38cqw;top:44px;width:100px"></div>'
        '<div class="dpe-nuage" style="right:18cqw;top:70px;width:70px"></div>'
        f'<div class="dpe-scene">{SCENE_SVG}</div>'
        '<div class="dpe-texte">'
        '<span class="dpe-pastille"><i></i>GreenTech Solutions pour Enedis</span>'
        '<div class="dpe-titre" role="heading" aria-level="1">'
        "Comprendre et prédire la performance énergétique des logements</div>"
        '<div class="dpe-paragraphe">'
        "Cette application explore les diagnostics de performance énergétique (DPE) publiés par l'ADEME "
        "pour les logements existants et neufs. Elle permet de comparer les consommations selon "
        "l'étiquette (de A, très performant, à G, très énergivore), la surface ou le département, "
        "puis d'estimer l'étiquette et la consommation d'un logement à partir de ses caractéristiques."
        "</div>"
        f'<div class="dpe-echelle">{pastilles}</div>'
        "</div>"
        "</div>"
    )
    st.html(f"<style>{CSS_BANNIERE}</style>")
    st.markdown(html, unsafe_allow_html=True)

CSS_FILTRES = """
/* Bande de filtres en haut de la page Statistiques */
.st-key-bande_filtres {
    background: #FFFFFF;
    border: 1px solid #E3EFCF;
    border-radius: 20px;
    padding: 10px 20px;
    gap: 1.4rem;
    flex-wrap: wrap;
    box-shadow: 0 6px 18px rgba(31, 107, 38, 0.10);
}
/* Les trois choix d'origine côte à côte au lieu d'être empilés */
.st-key-bande_filtres [data-testid="stRadio"] [role="radiogroup"] {
    flex-direction: row;
    gap: 1.2rem;
}
.st-key-bande_filtres [data-testid="stSelectbox"] {
    min-width: 220px;
}
"""


def habiller_filtres():
    """Applique le style de la bande de filtres (le contenant s'appelle « bande_filtres »)."""
    st.html(f"<style>{CSS_FILTRES}</style>")

COULEURS_ECHELLE = {
    "A": ("#319834", "#FFFFFF"),
    "B": ("#33CC31", "#FFFFFF"),
    "C": ("#CBFC34", "#17301B"),
    "D": ("#FBFE06", "#17301B"),
    "E": ("#FBCC05", "#17301B"),
    "F": ("#FC9935", "#17301B"),
    "G": ("#FC0205", "#FFFFFF"),
}

CSS_PREDICTION = """
/* Formulaire : pas de cadre autour du formulaire entier */
[data-testid="stForm"] {
    border: none;
    padding: 0;
}

/* Étapes du formulaire : les onglets deviennent une frise d'icônes reliées par un trait dégradé.
   On vise les rôles d'accessibilité (role="tab"...) : ils ne changent pas d'une version de Streamlit à l'autre. */
.st-key-etapes {
    background: #FFFFFF;
    border: 1px solid #E3EFCF;
    border-radius: 24px;
    padding: 14px 10px 22px;
    box-shadow: 0 8px 20px -16px rgba(31, 107, 38, 0.4);
    gap: 0;
}
.st-key-etapes [role="tablist"] {
    position: relative;
    display: flex;
    gap: 0;
    justify-content: space-between;
    overflow: visible !important;
    padding: 10px 0 0;
    border-bottom: 1px solid #E3EFCF;
}
.st-key-etapes [role="tablist"]::before {
    content: "";
    position: absolute;
    left: 8.33%;
    right: 8.33%;
    top: 29px;
    height: 4px;
    border-radius: 4px;
    background: linear-gradient(90deg, #319834, #CBFC34, #FBCC05, #FC9935);
}
.st-key-etapes [role="tab"] {
    position: relative;
    z-index: 1;
    flex: 1 1 0;
    min-width: 0;
    height: auto !important;
    margin: 0 !important;
    padding: 0 2px 12px !important;
    background: transparent;
    border-bottom: 3px solid transparent;
}
.st-key-etapes [role="tab"] p {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin: 0;
    text-align: center;
    font-size: 13.5px;
    line-height: 1.25;
    color: #4D6150;
}
.st-key-etapes [role="tab"] p::after {
    font-size: 11.5px;
    font-weight: 400;
    color: #7B8B7D;
}
.st-key-etapes [role="tab"] p > :first-child {
    width: 42px;
    height: 42px;
    box-sizing: border-box;
    margin: 0;
    border-radius: 50%;
    border: 2px solid #CFE4B8;
    background: #FFFFFF;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #4D6150;
}
.st-key-etapes [role="tab"] p > :first-child,
.st-key-etapes [role="tab"] p > :first-child * {
    font-size: 20px !important;
}

.st-key-etapes [role="tab"][aria-selected="true"] {
    border-bottom-color: #FC9935;
}
.st-key-etapes [role="tab"][aria-selected="true"] p {
    color: #17301B;
    font-weight: 700;
}
.st-key-etapes [role="tab"][aria-selected="true"] p > :first-child {
    background: #FC9935;
    border-color: #FC9935;
    color: #17301B;
    box-shadow: 0 0 0 5px #FFE6CA;
}
/* le soulignement est dessiné par le bas de l'onglet : on cache celui de Streamlit pour ne pas le doubler */
.st-key-etapes [role="tablist"] > :not([role="tab"]) {
    display: none !important;
}
.st-key-etapes [role="tabpanel"] {
    padding: 22px 18px 0;
}

/* En-tête de chaque étape : pastille d'icône, titre et description */
[class*="st-key-icone_etape_"] {
    flex: none;
    width: 52px !important;
    height: 52px !important;
    min-height: 52px !important;
    border-radius: 14px;
    background: #FFF0D2;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    gap: 0;
}

[class*="st-key-icone_etape_"] * {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    line-height: 1;
    text-align: center;
    font-size: 26px !important;
}
/* le symbole lui-même : une grille centre son contenu quel que soit l'affichage choisi par Streamlit */
[class*="st-key-icone_etape_"] [data-testid="stIconMaterial"] {
    display: grid !important;
    place-items: center;
}
.etape-texte {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
}
.etape-texte b {
    font-size: 20px;
    font-weight: 700;
    line-height: 1.2;
    color: #17301B;
}
.etape-texte span {
    font-size: 13.5px;
    color: #4D6150;
}


/* Champs du formulaire : fond vert très clair, sans cadre */
.st-key-etapes [data-baseweb="input"],
.st-key-etapes [data-baseweb="select"] > div {
    background: #F6FAE9;
    border-color: transparent;
    border-radius: 10px;
}

/* Colonne de droite : le résultat reste visible pendant la saisie */
.st-key-panneau_droit {
    position: sticky;
    top: 1rem;
    gap: 0.9rem;
}
.st-key-panneau_resultat {
    background: linear-gradient(180deg, #FFF4DC, #FFE9CB);
    border-radius: 28px;
    border-bottom: 6px solid #FC9935;
    padding: 20px 22px 22px;
    box-shadow: 0 18px 34px -22px rgba(252, 153, 53, 0.7);
    gap: 0.7rem;
}
.st-key-bloc_modeles {
    background: #FFFFFF;
    border: 1px solid #E3EFCF;
    border-radius: 20px;
    padding: 14px 18px;
    gap: 0.4rem;
}

/* Résultat : grande tuile d'étiquette, consommation, échelle A à G */
.res-haut {
    display: flex;
    gap: 18px;
    align-items: center;
}
.res-tuile {
    width: 88px;
    height: 88px;
    flex: none;
    border-radius: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 50px;
    font-weight: 700;
    box-shadow: 0 10px 16px -10px rgba(0, 0, 0, 0.35);
}
.res-tuile.vide {
    background: #FFFFFF;
    color: #9AA89C;
}
.res-textes small {
    display: block;
    font-size: 12.5px;
    color: #4D6150;
}
.res-textes small + small {
    margin-top: 6px;
}
.res-conso b {
    font-size: 36px;
    line-height: 1.1;
}
.res-conso span {
    font-size: 13px;
    color: #4D6150;
}
.dpe-ech {
    margin-top: 14px;
}
.dpe-ligne {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
}
.dpe-lt {
    height: 34px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    padding-left: 12px;
    font-weight: 700;
    font-size: 14px;
}
.dpe-lt.neutre { opacity: 0.4; }
.dpe-lt.estompee { opacity: 0.42; }
.dpe-lt.choisie {
    height: 42px;
    font-size: 20px;
    box-shadow: 0 10px 16px -10px rgba(0, 0, 0, 0.4);
}
.dpe-ligne em {
    font-style: normal;
    font-size: 13px;
    font-weight: 700;
    color: #17301B;
    white-space: nowrap;
}

/* Fiabilité du modèle : jauge en demi-cercle */
.jauge {
    background: #FFFFFF;
    border-radius: 18px;
    padding: 14px 16px 12px;
    text-align: center;
}
.jauge-titre {
    font-size: 13.5px;
    font-weight: 600;
}
.jauge svg {
    display: block;
    margin: 6px auto 0;
}
.jauge-valeur {
    font-size: 32px;
    font-weight: 700;
    line-height: 1;
    margin-top: -38px;
    margin-bottom: 4px;
    position: relative;
}
.jauge p {
    margin: 12px 0 0;
    font-size: 12.5px;
    color: #4D6150;
}
"""

# Écran étroit : les étapes passent à la ligne, 3 par rangée, au lieu d'être serrées sur une seule ligne.
# On teste la largeur du cadre du formulaire (container query), pas celle de la fenêtre :
# la colonne du formulaire est étroite bien avant le téléphone.
CSS_PREDICTION_ETROIT = """
.st-key-etapes {
    container-type: inline-size;
}
/* cadre un peu étroit : les six étapes restent sur une ligne, avec des libellés plus petits */
@container (max-width: 640px) {
    .st-key-etapes [role="tab"] p {
        font-size: 12px;
    }
    .st-key-etapes [role="tab"] p::after {
        font-size: 10.5px;
    }
}
/* cadre très étroit (téléphone) : les étapes passent à la ligne, 3 par rangée */
@container (max-width: 400px) {
    .st-key-etapes [role="tablist"] {
        flex-wrap: wrap;
        justify-content: flex-start;
        row-gap: 16px;
    }
    /* le trait dégradé relie les étapes sur une seule ligne : il n'a plus de sens sur plusieurs */
    .st-key-etapes [role="tablist"]::before {
        display: none;
    }
    .st-key-etapes [role="tab"] {
        flex: 0 0 33.333%;
    }
    .st-key-etapes [role="tab"] p {
        overflow-wrap: anywhere;
    }
}
"""

def habiller_prediction(nombres_champs=()):
    """Applique le style de la page Prédiction.

    nombres_champs : le nombre de champs de chaque étape, dans l'ordre des onglets.
    Il est écrit sous le nom de chaque onglet (« 5 champs »)."""
    compteurs = ""
    for rang, nombre in enumerate(nombres_champs, start=1):
        mot = "champ" if nombre == 1 else "champs"
        compteurs += (
            f'.st-key-etapes [role="tab"]:nth-of-type({rang}) p::after {{ content: "{nombre} {mot}"; }}\n'
        )
    if nombres_champs:
        # le trait dégradé va du centre du premier onglet au centre du dernier
        marge = 50 / len(nombres_champs)
        compteurs += f'.st-key-etapes [role="tablist"]::before {{ left: {marge:.2f}%; right: {marge:.2f}%; }}\n'
    st.html(f"<style>{CSS_FILTRES}{CSS_PREDICTION}{compteurs}{CSS_PREDICTION_ETROIT}</style>")


def echelle_dpe(etiquette=None):
    """Échelle A à G en barres. Sans étiquette, toutes les barres sont grisées ;
    avec une étiquette, elle ressort et les autres s'estompent."""
    lignes = ""
    for rang, (lettre, (fond, texte)) in enumerate(COULEURS_ECHELLE.items()):
        if etiquette is None:
            classe, marque = "neutre", ""
        elif lettre == etiquette:
            classe, marque = "choisie", "<em>◀ Votre logement</em>"
        else:
            classe, marque = "estompee", ""
        largeur = 48 + rang * 8
        lignes += (
            f'<div class="dpe-ligne"><div class="dpe-lt {classe}" style="width:{largeur}%;background:{fond};'
            f'color:{texte}">{lettre}</div>{marque}</div>'
        )
    description = f"Étiquette estimée : {etiquette}" if etiquette else "Échelle des étiquettes DPE, de A à G"
    return f'<div class="dpe-ech" role="img" aria-label="{description}">{lignes}</div>'


def tuile_resultat(etiquette=None, consommation=None, avec_etiquette=True, avec_consommation=True):
    """En-tête du résultat : tuile de l'étiquette estimée et consommation estimée.
    Sans valeur (avant l'estimation), la tuile affiche « ? » et la consommation « — »."""
    tuile = textes = ""
    if avec_etiquette:
        if etiquette:
            fond, texte = COULEURS_ECHELLE[etiquette]
            tuile = f'<div class="res-tuile" style="background:{fond};color:{texte}">{etiquette}</div>'
        else:
            tuile = '<div class="res-tuile vide">?</div>'
        textes += "<small>Étiquette estimée</small>"
    if avec_consommation:
        valeur = "—" if consommation is None else f"{consommation:.0f}"
        textes += (
            f'<small>Consommation estimée</small><div class="res-conso"><b>{valeur}</b> '
            "<span>kWh/m²/an</span></div>"
        )
    return f'<div class="res-haut">{tuile}<div class="res-textes">{textes}</div></div>'


def jauge_fiabilite(pourcentage, nom_departement):
    """Jauge en demi-cercle : part des logements dont l'étiquette est devinée exactement."""
    pourcentage = max(0.0, min(100.0, float(pourcentage)))
    angle = math.radians(180 * pourcentage / 100)
    # demi-cercle de centre (60, 62) et de rayon 50 ; (x, y) est le bout de l'arc coloré
    x = 60 - 50 * math.cos(angle)
    y = 62 - 50 * math.sin(angle)
    arc = f'<path d="M10 62 A50 50 0 0 1 {x:.1f} {y:.1f}" stroke="url(#jauge-degrade)" stroke-width="12" fill="none" stroke-linecap="round"/>'
    return (
        '<div class="jauge">'
        f'<div class="jauge-titre">Fiabilité du modèle ({nom_departement})</div>'
        '<svg width="170" height="88" viewBox="0 0 120 70" aria-hidden="true">'
        '<defs><linearGradient id="jauge-degrade" x1="0" x2="1"><stop offset="0" stop-color="#FC9935"/>'
        '<stop offset="0.5" stop-color="#FBCC05"/><stop offset="1" stop-color="#319834"/></linearGradient></defs>'
        '<path d="M10 62 A50 50 0 0 1 110 62" stroke="#E3EFCF" stroke-width="12" fill="none" stroke-linecap="round"/>'
        f"{arc}</svg>"
        f'<div class="jauge-valeur">{pourcentage:.0f} %</div>'
        "<p>Part des logements dont l'étiquette est devinée exactement.</p>"
        "</div>"
    )


# PAGE CONTEXTE : titres en rubans d'étiquette DPE, tuiles de chiffres, blocs dépliables en cartes
# Couleur du ruban de chaque titre, du haut vers le bas de la page (des verts vers le jaune)
RUBANS_CONTEXTE = {
    "ruban_presentation": "#93CC84",
    "ruban_carte": "#A9D882",
    "ruban_rafraichir": "#CBE77E",
    "ruban_apercu": "#F6E270",
}
# Fond de chaque tuile de chiffre, de gauche à droite
TUILES_CONTEXTE = ["#C4E3B3", "#E0F2A0", "#FCE893", "#FBCFA0"]

CSS_CONTEXTE = """
/* Ligne du snapshot : une rangée de pastilles blanches (snapshot, date, départements) */
.snap-ligne {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 4px 0 6px;
}
.snap-puce {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: #FFFFFF;
    border: 1px solid #E3EFCF;
    border-radius: 999px;
    padding: 7px 15px;
    font-size: 13px;
    color: #4D6150;
    box-shadow: 0 6px 12px -10px rgba(31, 107, 38, 0.5);
}
.snap-puce b {
    font-weight: 600;
    color: #17301B;
}
.snap-puce svg {
    flex: none;
    color: #319834;
}

/* Titres de section : un ruban en forme d'étiquette DPE (pointe à droite) */
[class*="st-key-ruban_"] {
    margin-top: 1.2rem;
    margin-bottom: 0.4rem;
}
[class*="st-key-ruban_"] h3 {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    width: fit-content;
    margin: 0;
    padding: 11px 48px 11px 14px;
    font-size: 20px;
    font-weight: 700;
    color: #17301B;
    border-radius: 14px 0 0 14px;
    clip-path: polygon(0 0, calc(100% - 22px) 0, 100% 50%, calc(100% - 22px) 100%, 0 100%);
}
[class*="st-key-ruban_"] h3 [data-testid="stIconMaterial"] {
    width: 34px;
    height: 34px;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.55);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
}

/* Les quatre chiffres : des tuiles colorées, l'icône reste à gauche du titre */
.st-key-chiffres [data-testid="stMetric"] {
    border-radius: 24px;
    padding: 18px 20px;
    border: 1px solid rgba(23, 48, 27, 0.06);
    box-shadow: 0 10px 20px -18px rgba(31, 107, 38, 0.5);
}
.st-key-chiffres [data-testid="stMetricValue"] {
    color: #1F5A2A;
    font-weight: 700;
}
.st-key-chiffres [data-testid="stMetricLabel"] {
    color: #2F4D33;
}

/* Blocs dépliables (résumé, filtres, rafraîchissement, limites) : des cartes blanches arrondies */
[data-testid="stExpander"] details {
    background: #FFFFFF;
    border: 1px solid #E3EFCF;
    border-radius: 20px;
    box-shadow: 0 8px 20px -16px rgba(31, 107, 38, 0.4);
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    padding: 14px 20px;
}

/* Curseur de surface : en rouge (on fait tourner la teinte du vert vers le rouge) */
.st-key-surface [data-testid="stSlider"] {
    filter: hue-rotate(260deg) saturate(4) brightness(0.82);
}
"""


def habiller_contexte():
    """Applique le style de la page Contexte : rubans, tuiles de chiffres, cartes dépliables, curseur rouge."""
    regles = ""
    for nom, couleur in RUBANS_CONTEXTE.items():
        regles += f".st-key-{nom} h3 {{ background: {couleur}; }}\n"
    for rang, fond in enumerate(TUILES_CONTEXTE, start=1):
        colonne = f'.st-key-chiffres [data-testid="stColumn"]:nth-child({rang})'
        regles += f'{colonne} [data-testid="stMetric"] {{ background: {fond}; }}\n'
    st.html(f"<style>{CSS_CONTEXTE}{regles}</style>")



# Fond de chaque tuile de la page Statistiques, de gauche à droite (mêmes tons que Contexte, plus un rose)
TUILES_STATISTIQUES = ["#C4E3B3", "#E0F2A0", "#FCE893", "#FBCFA0", "#F8BBA6"]


def habiller_chiffres_statistiques():
    """Style des 5 chiffres clés de la page Statistiques

    Les chiffres sont dans un conteneur nommé « chiffres_stats » (voir statistiques.py)."""
    base = """
.st-key-chiffres_stats [data-testid="stMetric"] {
    border-radius: 24px;
    padding: 18px 20px;
    border: 1px solid rgba(23, 48, 27, 0.06);
    box-shadow: 0 10px 20px -18px rgba(31, 107, 38, 0.5);
}
.st-key-chiffres_stats [data-testid="stMetricValue"] {
    color: #1F5A2A;
    font-weight: 700;
}
.st-key-chiffres_stats [data-testid="stMetricLabel"] {
    color: #2F4D33;
}
"""
    regles = ""
    for rang, fond in enumerate(TUILES_STATISTIQUES, start=1):
        colonne = f'.st-key-chiffres_stats [data-testid="stColumn"]:nth-child({rang})'
        regles += f'{colonne} [data-testid="stMetric"] {{ background: {fond}; }}\n'
    st.html(f"<style>{base}{regles}</style>")


# Petit repère de carte (SVG) placé devant chaque département
PICTO_LIEU = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 21s7-6.2 7-11.5A7 7 0 005 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>'
)


def ligne_snapshot(snapshot, date_telechargement, noms_departements):
    """Première ligne de la page Contexte : une rangée de pastilles (HTML) avec les mêmes informations qu'avant."""
    puces = [
        f'<span class="snap-puce">Données du snapshot <b>{snapshot}</b></span>',
        f'<span class="snap-puce">Téléchargé le <b>{date_telechargement}</b></span>',
    ]
    if noms_departements:
        puces += [f'<span class="snap-puce">{PICTO_LIEU}<b>{nom}</b></span>' for nom in noms_departements]
    else:
        puces.append('<span class="snap-puce">départements non précisés</span>')
    # écrit sur une seule ligne : un retour à la ligne vide casserait le HTML dans Streamlit
    return f'<div class="snap-ligne">{"".join(puces)}</div>'