"""
Prétraitement des DPE (logements neufs et existants).

- Les fonctions de règle reçoivent un DataFrame et en renvoient un, sans lire ni
  écrire de fichier : elles servent au nettoyage initial, au rafraîchissement des
  données dans l'app et au réentraînement.
- La classe DataPreprocessor fusionne neufs et existants par département, puis
  applique ces règles.
Les décisions et leurs justifications sont documentées dans
notebooks/02_nettoyage_donnees.ipynb et docs/colonnes_retenues.csv.
"""
import warnings
import pandas as pd

# ---------------------------------------------------------------------------
# Colonnes conservées (30 sur 224)
# ---------------------------------------------------------------------------
# Colonnes pour l'analyse seulement : elles contiennent déjà la réponse ou sont
# des résultats de calcul du DPE. À EXCLURE des variables d'entrée des modèles.
COLONNES_ANALYSE = [
    "etiquette_ges", "emission_ges_5_usages_par_m2", "conso_5_usages_ep",
    "conso_chauffage_ep", "conso_ecs_ep", "conso_eclairage_ep",
    "conso_auxiliaires_ep", "cout_total_5_usages", "ubat_w_par_m2_k",
]
COLONNES_GARDEES = [
    "numero_dpe", "date_reception_dpe", "origine",                  # identification
    "etiquette_dpe", "conso_5_usages_par_m2_ep",                    # cibles
    "code_departement_ban", "code_postal_ban", "nom_commune_ban",   # géographie
    "code_insee_ban", "_geopoint",
    "surface_habitable_logement", "periode_construction",           # logement
    "type_batiment", "hauteur_sous_plafond",
    "type_energie_principale_chauffage", "type_installation_chauffage",
    "type_installation_ecs",                                        # chauffage, eau chaude
    "qualite_isolation_enveloppe", "qualite_isolation_murs",        # isolation
    "qualite_isolation_menuiseries", "qualite_isolation_plancher_bas",
] + COLONNES_ANALYSE

# ---------------------------------------------------------------------------
# Seuils (justifiés dans le notebook)
# ---------------------------------------------------------------------------
SURFACE_MIN, SURFACE_MAX = 5, 500          # m² : en dessous, pas un logement ; au-dessus, erreurs
CONSO_MAX = 1000                           # kWh/m²/an
GES_MAX = 1000                             # kg CO2/m²/an (les erreurs de Lyon dépassent 5 900)
HAUTEUR_MIN, HAUTEUR_MAX = 1.8, 5          # m ; hors de cette plage : unité erronée probable
LAT_MIN, LAT_MAX = 41, 52                  # France métropolitaine
LON_MIN, LON_MAX = -5.5, 10

COLONNES_OBLIGATOIRES = ["numero_dpe", "etiquette_dpe",
                         "conso_5_usages_par_m2_ep", "surface_habitable_logement"]
COLONNES_NUMERIQUES = ["conso_5_usages_par_m2_ep", "surface_habitable_logement",
                       "emission_ges_5_usages_par_m2", "hauteur_sous_plafond"]
COLONNES_CATEGORIELLES = [
    "periode_construction", "type_batiment", "type_energie_principale_chauffage",
    "type_installation_chauffage", "type_installation_ecs",
    "qualite_isolation_enveloppe", "qualite_isolation_murs",
    "qualite_isolation_menuiseries", "qualite_isolation_plancher_bas",
]

# Ordres des catégories ordonnées (pour les filtres et les graphiques)
ORDRE_PERIODE = ["avant 1948", "1948-1974", "1975-1977", "1978-1982", "1983-1988",
                 "1989-2000", "2001-2005", "2006-2012", "2013-2021", "après 2021"]
ORDRE_ISOLATION = ["insuffisante", "moyenne", "bonne", "très bonne"]



# Règles de nettoyage : une fonction par règle, DataFrame en entrée et en sortie

def garder_colonnes(df):
    """Ne garde que les colonnes utiles à l'application (liste blanche)."""
    return df[[c for c in COLONNES_GARDEES if c in df.columns]].copy()

def convertir_types(df):
    """Nombres et dates : les valeurs illisibles deviennent manquantes."""
    df = df.copy()
    for col in COLONNES_NUMERIQUES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date_reception_dpe"] = pd.to_datetime(df["date_reception_dpe"], errors="coerce")
    return df

def supprimer_doublons(df):
    return df.drop_duplicates(subset="numero_dpe")

def exclure_immeubles(df):
    """Un DPE d'immeuble décrit un bâtiment entier, pas un logement."""
    return df[df["type_batiment"] != "immeuble"]

def supprimer_manquants_cles(df):
    return df.dropna(subset=COLONNES_OBLIGATOIRES)

def filtrer_etiquettes(df):
    """Étiquettes valides : A à G."""
    df = df.copy()
    df["etiquette_dpe"] = df["etiquette_dpe"].astype("string").str.strip().str.upper()
    return df[df["etiquette_dpe"].isin(list("ABCDEFG"))]

def filtrer_surface(df):
    return df[df["surface_habitable_logement"].between(SURFACE_MIN, SURFACE_MAX)]

def filtrer_consommation(df):
    return df[(df["conso_5_usages_par_m2_ep"] > 0) & (df["conso_5_usages_par_m2_ep"] <= CONSO_MAX)]

def filtrer_emissions_ges(df):
    """Supprime les émissions impossibles (ex. 12 neufs de Lyon, étiquette G fausse).
    Les lignes sans valeur sont conservées."""
    return df[~(df["emission_ges_5_usages_par_m2"] > GES_MAX)]

def extraire_coordonnees(df):
    """_geopoint = 'latitude,longitude'. Les points hors de la France métropolitaine
    (position erronée commune à Lille et Lyon) deviennent manquants : la ligne est
    conservée mais n'apparaît pas sur la carte."""
    df = df.copy()
    coords = df["_geopoint"].astype("string").str.split(",", expand=True)
    if coords.shape[1] < 2:
        coords[1] = pd.NA
    lat = pd.to_numeric(coords[0], errors="coerce")
    lon = pd.to_numeric(coords[1], errors="coerce")
    valide = lat.between(LAT_MIN, LAT_MAX) & lon.between(LON_MIN, LON_MAX)
    df["latitude"] = lat.where(valide)
    df["longitude"] = lon.where(valide)
    return df.drop(columns="_geopoint")

def nettoyer_hauteur(df):
    """Hauteur hors de 1,8-5 m (souvent saisie en cm) : valeur manquante, ligne conservée."""
    df = df.copy()
    h = df["hauteur_sous_plafond"]
    df["hauteur_sous_plafond"] = h.where(h.between(HAUTEUR_MIN, HAUTEUR_MAX))
    return df

def regrouper_energie(valeur):
    """Regroupe les énergies de chauffage rares ou proches."""
    if pd.isna(valeur):
        return "Inconnu"
    v = str(valeur).strip()
    if v.startswith("Bois"):
        return "Bois"
    if v in {"Électricité", "Gaz naturel", "Réseau de Chauffage urbain",
             "Fioul domestique", "Non affecté"}:
        return v
    return "Autre"

def harmoniser_categories(df):
    """Espaces supprimés, énergies regroupées, installation manquante = 'non applicable'
    (colonne vide pour les maisons)."""
    df = df.copy()
    for col in COLONNES_CATEGORIELLES:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    df["type_energie_principale_chauffage"] = (
        df["type_energie_principale_chauffage"].map(regrouper_energie))
    for col in ["type_installation_chauffage", "type_installation_ecs", "qualite_isolation_plancher_bas"]:
        df[col] = df[col].fillna("non applicable")
    return df


def supprimer_manquants_restants(df):
    """Filet de sécurité : supprime les lignes qui ont encore une valeur manquante
    (latitude, longitude, hauteur, ou une colonne imprévue d'un futur scrape).
    Une colonne entièrement vide est laissée telle quelle, avec un avertissement,
    sinon toutes les lignes seraient supprimées."""
    vides = [c for c in df.columns if df[c].isna().all()]
    if vides:
        warnings.warn(f"Colonnes entièrement vides (ignorées par le filet) : {vides}")
    return df.dropna(subset=[c for c in df.columns if c not in vides])


def nettoyer(df, bilan=None):
    """Un département fusionné (brut) -> DataFrame propre.
    Si `bilan` est une liste, on y ajoute (règle, nombre de lignes) après chaque étape."""
    if bilan is None:
        bilan = []

    def etape(d, nom):
        bilan.append((nom, len(d)))
        return d

    df = etape(df, "Données brutes")
    df = etape(garder_colonnes(df), "Sélection des 30 colonnes")
    df = etape(convertir_types(df), "Conversion des types")
    df = etape(supprimer_doublons(df), "Doublons supprimés")
    df = etape(exclure_immeubles(df), "Immeubles exclus")
    df = etape(supprimer_manquants_cles(df), "Manquants clés supprimés")
    df = etape(filtrer_etiquettes(df), "Étiquettes A-G")
    df = etape(filtrer_surface(df), f"Surface {SURFACE_MIN}-{SURFACE_MAX} m²")
    df = etape(filtrer_consommation(df), f"Consommation ≤ {CONSO_MAX}")
    df = etape(filtrer_emissions_ges(df), f"Émissions GES ≤ {GES_MAX}")
    df = etape(extraire_coordonnees(df), "Coordonnées extraites")
    df = etape(nettoyer_hauteur(df), "Hauteur sous plafond")
    df = etape(harmoniser_categories(df), "Catégories harmonisées")
    df = etape(supprimer_manquants_restants(df), "Manquants restants supprimés")
    return df.reset_index(drop=True)



# Classe utilisée par le reste du projet (interface inchangée)

class DataPreprocessor():
    """
    Preprocesses the data for analysis and modeling.
    """

    def __init__(self, appliquer_nettoyage: bool = True):
        """
        Args:
            appliquer_nettoyage: si False, on garde le comportement provisoire
                (fusion seulement, toutes les colonnes brutes).
        """
        self.appliquer_nettoyage = appliquer_nettoyage
        self.bilans = {}   # {departement: DataFrame du bilan} après process()

    def fusionner(self, datasets: dict) -> dict:
        """Fusionne les datasets de chaque département ; la colonne "origine"
        contient le nom du dataset (ex. "dpe_existants")."""
        return {
            departement: pd.concat(
                [df.assign(origine=name) for name, df in dfs.items()], ignore_index=True)
            for departement, dfs in datasets.items()
        }

    def process(self, datasets: dict) -> dict:
        """
        Args:
            datasets: {departement: {nom_dataset: DataFrame}}

        Returns:
            {departement: DataFrame}  (fusionné, puis nettoyé si appliquer_nettoyage)
        """
        fusionnes = self.fusionner(datasets)
        if not self.appliquer_nettoyage:
            return fusionnes

        resultat = {}
        for departement, df in fusionnes.items():
            bilan = []
            resultat[departement] = nettoyer(df, bilan)
            self.bilans[departement] = pd.DataFrame(
                bilan, columns=["etape", "lignes"]).set_index("etape")
        return resultat
