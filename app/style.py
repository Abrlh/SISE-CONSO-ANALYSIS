"""Style de l'application : l'habillage du menu de gauche, les cartes et la bannière de l'Accueil.

Le style est du CSS (la langue des couleurs et des mises en forme du web), envoyé à Streamlit sous
forme de texte. La bannière utilise aussi du HTML (la structure) et un dessin SVG (des formes dessinées
par des coordonnées). Les couleurs viennent des étiquettes DPE de l'application. Aucun calcul ici.
"""
import streamlit as st

# ---------------------------------------------------------------------------------------------
# MENU DE GAUCHE
# ---------------------------------------------------------------------------------------------
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
/* Moins d'espace vide autour du contenu : Streamlit en laisse beaucoup par défaut */
[data-testid="stMainBlockContainer"] {
    padding-top: 1.4rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
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


# ---------------------------------------------------------------------------------------------
# CARTES DE L'ACCUEIL : trois cartes numérotées, cliquables en entier
# ---------------------------------------------------------------------------------------------
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
    """Affiche en bas du menu de gauche la source des données et les auteures du projet."""
    with st.sidebar:
        st.markdown(
            '<div style="font-size:12px;line-height:1.5;color:#4D6150">'
            "Source des données : ADEME, DPE des logements existants et neufs."
            '<br><br>Projet M2 SISE<br>Présenté par :<br>Clara FONTAINE<br>'
            "Aissatou Lamarana BARRY<br>Nicole NGEJEJE</div>",
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

# ---------------------------------------------------------------------------------------------
# Le dessin (SVG) : un logement existant, un logement neuf, une éolienne, un poteau électrique
# et une borne de recharge. Chaque ligne est une forme.
# ---------------------------------------------------------------------------------------------
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
/* Formulaire : pas de cadre autour du formulaire entier, une carte blanche par groupe de champs */
[data-testid="stForm"] {
    border: none;
    padding: 0;
}
[class*="st-key-groupe_"] {
    background: #FFFFFF;
    border: 1px solid #E3EFCF;
    border-radius: 20px;
    padding: 16px 20px 12px;
    box-shadow: 0 6px 18px rgba(31, 107, 38, 0.06);
    gap: 0.4rem;
}
[class*="st-key-groupe_"] strong {
    font-size: 16px;
}

/* Colonne de droite : le résultat reste visible pendant la saisie */
.st-key-panneau_droit {
    position: sticky;
    top: 1rem;
    gap: 0.9rem;
}
.st-key-panneau_resultat {
    background: linear-gradient(180deg, #FFF6DF, #FFE9C4);
    border-radius: 24px;
    border-bottom: 5px solid #FC9935;
    padding: 18px 20px 20px;
    box-shadow: 0 14px 30px -20px rgba(120, 70, 0, 0.45);
    gap: 0.6rem;
}
.st-key-bloc_modeles {
    background: #FFFFFF;
    border: 1px solid #E3EFCF;
    border-radius: 20px;
    padding: 14px 18px;
    gap: 0.4rem;
}

/* Échelle A à G : l'étiquette estimée sort de la rangée */
.dpe-ech {
    display: flex;
    gap: 6px;
    padding: 28px 0 8px;
}
.dpe-lt {
    flex: 1;
    height: 50px;
    border-radius: 14px;
    font-weight: 700;
    font-size: 19px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}
.dpe-lt.neutre { opacity: 0.45; }
.dpe-lt.estompee { opacity: 0.35; }
.dpe-lt.choisie {
    transform: translateY(-6px) scale(1.14);
    box-shadow: 0 0 0 4px #FFFFFF, 0 10px 18px -8px rgba(0, 0, 0, 0.4);
    z-index: 2;
}
.dpe-lt em {
    position: absolute;
    top: -26px;
    left: 50%;
    transform: translateX(-50%);
    font-style: normal;
    font-size: 11px;
    font-weight: 600;
    color: #17301B;
    white-space: nowrap;
}
"""


def habiller_prediction():
    """Applique le style de la page Prédiction (avec celui de la bande de filtres)."""
    st.html(f"<style>{CSS_FILTRES}{CSS_PREDICTION}</style>")


def echelle_dpe(etiquette=None):
    """Échelle A à G en HTML. Sans étiquette, toutes les pastilles sont grisées ;
    avec une étiquette, elle ressort et les autres s'estompent."""
    pastilles = ""
    for lettre, (fond, texte) in COULEURS_ECHELLE.items():
        if etiquette is None:
            classe, marque = "neutre", ""
        elif lettre == etiquette:
            classe, marque = "choisie", "<em>Votre logement</em>"
        else:
            classe, marque = "estompee", ""
        pastilles += f'<div class="dpe-lt {classe}" style="background:{fond};color:{texte}">{lettre}{marque}</div>'
    description = f"Étiquette estimée : {etiquette}" if etiquette else "Échelle des étiquettes DPE, de A à G"
    return f'<div class="dpe-ech" role="img" aria-label="{description}">{pastilles}</div>'