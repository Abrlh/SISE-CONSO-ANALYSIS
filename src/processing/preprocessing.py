"""
Prétraitement des DPE : DataPreprocessor fusionne neufs et existants par département,
puis applique les règles (une fonction par règle, sans accès aux fichiers).

Toutes les colonnes sont gardées sauf les trop vides (SEUIL_MANQUANT) ; aucune imputation ici.
Justification des règles : docs/nettoyage_donnees.md.
"""
import pandas as pd

# ---------------------------------------------------------------------------
# Colonnes
# ---------------------------------------------------------------------------
# Pas de liste blanche : toutes les colonnes sont gardées, sauf celles qui sont trop
# vides (voir SEUIL_MANQUANT).
# AVERTISSEMENT : ces 9 colonnes (et, plus largement, toutes celles qui commencent par
# conso_, cout_, emission_ges, etiquette_, deperditions, besoin, ubat) contiennent la
# réponse ou sont des résultats du calcul du DPE. Utiles pour l'analyse, mais à
# EXCLURE des variables d'entrée des modèles.

COLONNES_ANALYSE = [
    "etiquette_ges", "emission_ges_5_usages_par_m2", "conso_5_usages_ep",
    "conso_chauffage_ep", "conso_ecs_ep", "conso_eclairage_ep",
    "conso_auxiliaires_ep", "cout_total_5_usages", "ubat_w_par_m2_k",
]

# ---------------------------------------------------------------------------
# Seuils (justifiés dans le notebook)
# ---------------------------------------------------------------------------
SURFACE_MIN, SURFACE_MAX = 5, 500          # m² : en dessous, pas un logement ; au-dessus, erreurs
CONSO_MAX = 1000                           # kWh/m²/an
GES_MAX = 1000                             # kg CO2/m²/an (les erreurs de Lyon dépassent 5 900)
HAUTEUR_MIN, HAUTEUR_MAX = 1.8, 5          # m ; hors de cette plage : unité erronée probable
LAT_MIN, LAT_MAX = 41, 52                  # France métropolitaine
LON_MIN, LON_MAX = -5.5, 10
SEUIL_MANQUANT = 0.8                       # une colonne vide à plus de 80 % est retirée
TYPES_BATIMENT_EXCLUS = ["immeuble"]       # [] pour garder les immeubles

COLONNES_OBLIGATOIRES = ["numero_dpe", "etiquette_dpe",
                         "conso_5_usages_par_m2_ep", "surface_habitable_logement"]
# colonnes créées par le nettoyage -> colonne brute dont elles viennent (None : ajoutée par la fusion)
# (sert à l'audit, qui contrôle les données brutes)
COLONNES_CREEES = {"origine": None, "latitude": "_geopoint", "longitude": "_geopoint"}
COLONNES_NUMERIQUES = ["conso_5_usages_par_m2_ep", "surface_habitable_logement",
                       "emission_ges_5_usages_par_m2", "hauteur_sous_plafond"]
# Ordres des catégories ordonnées (pour les filtres et les graphiques)
ORDRE_PERIODE = ["avant 1948", "1948-1974", "1975-1977", "1978-1982", "1983-1988",
                 "1989-2000", "2001-2005", "2006-2012", "2013-2021", "après 2021"]
ORDRE_ISOLATION = ["insuffisante", "moyenne", "bonne", "très bonne"]



class ColonnesManquantesError(ValueError):
    """Colonnes attendues par le code mais absentes des données (`colonnes` : leur liste)."""

    def __init__(self, colonnes, contexte):
        self.colonnes = colonnes
        super().__init__(f"{contexte} absentes des données : {colonnes}")


def verifier_colonnes(df, colonnes, contexte):
    """Lève ColonnesManquantesError si une des `colonnes` manque dans df ; sinon renvoie df."""
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte)
    return df


# Règles de nettoyage : une fonction par règle, DataFrame en entrée et en sortie

def verifier_colonnes_obligatoires(df):
    """Arrête le nettoyage avec un message clair si une colonne indispensable manque."""
    return verifier_colonnes(df, COLONNES_OBLIGATOIRES, "Colonnes indispensables")

def convertir_types(df):
    """Nombres et dates : les valeurs illisibles deviennent manquantes."""
    df = df.copy()
    for col in COLONNES_NUMERIQUES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "date_reception_dpe" in df.columns:
        df["date_reception_dpe"] = pd.to_datetime(df["date_reception_dpe"], errors="coerce")
    return df

def supprimer_doublons(df):
    return df.drop_duplicates(subset="numero_dpe")

def exclure_immeubles(df):
    """Un DPE d'immeuble décrit un bâtiment entier, pas un logement (voir
    TYPES_BATIMENT_EXCLUS : liste vide pour les garder)."""
    if "type_batiment" not in df.columns or not TYPES_BATIMENT_EXCLUS:
        return df
    return df[~df["type_batiment"].isin(TYPES_BATIMENT_EXCLUS)]

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
    if "emission_ges_5_usages_par_m2" not in df.columns:
        return df
    return df[~(df["emission_ges_5_usages_par_m2"] > GES_MAX)]

def extraire_coordonnees(df):
    """Extrait latitude et longitude de _geopoint ; hors métropole, la position devient manquante."""
    if "_geopoint" not in df.columns:
        return df
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
    if "hauteur_sous_plafond" not in df.columns:
        return df
    df = df.copy()
    h = df["hauteur_sous_plafond"]
    df["hauteur_sous_plafond"] = h.where(h.between(HAUTEUR_MIN, HAUTEUR_MAX))
    return df

def supprimer_espaces(df):
    """Espaces en début et fin de texte supprimés, dans toutes les colonnes de texte
    (y compris celles qui apparaîtront dans de futurs rafraîchissements)."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.infer_dtype(df[col], skipna=True) == "string":
            df[col] = df[col].str.strip()
    return df

def retirer_colonnes_vides(df, retirees=None):
    """Retire les colonnes avec plus de SEUIL_MANQUANT de valeurs manquantes (sauf obligatoires).

    Args:
        retirees: si c'est une liste, on y ajoute (colonne, % manquant)
    """
    taux = df.isna().mean()
    a_retirer = [c for c in df.columns
                 if taux[c] > SEUIL_MANQUANT and c not in COLONNES_OBLIGATOIRES]
    if retirees is not None:
        retirees.extend((c, round(100 * taux[c], 1)) for c in a_retirer)
    return df.drop(columns=a_retirer)


def nettoyer(df, bilan=None, colonnes_retirees=None):
    """Nettoie un département fusionné.

    Args:
        bilan: si c'est une liste, on y ajoute (règle, nombre de lignes) après chaque étape
        colonnes_retirees: si c'est une liste, on y ajoute (colonne, % manquant)
    """
    if bilan is None:
        bilan = []

    def etape(d, nom):
        bilan.append((nom, len(d)))
        return d

    df = etape(verifier_colonnes_obligatoires(df), "Données brutes")
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
    df = etape(supprimer_espaces(df), "Espaces supprimés")
    df = etape(retirer_colonnes_vides(df, colonnes_retirees),
               f"Colonnes vides à plus de {int(SEUIL_MANQUANT * 100)} % retirées")
    return df.reset_index(drop=True)



# Classe utilisée par le reste du projet (interface inchangée)

class DataPreprocessor():
    """Prétraite les données pour l'analyse et la modélisation."""

    def __init__(self, appliquer_nettoyage: bool = True):
        """
        Args:
            appliquer_nettoyage: si False, on garde le comportement provisoire
                (fusion seulement, toutes les colonnes brutes).
        """
        self.appliquer_nettoyage = appliquer_nettoyage
        self.bilans = {}   # {departement: DataFrame du bilan} après process()
        self.colonnes_retirees = {}   # {departement: DataFrame (colonne, % manquant)}


    def rapport(self) -> dict:
        """Bilan du dernier process(), enregistré dans meta.json.

        Returns:
            {departement: {"bilan": [[étape, lignes]], "colonnes_retirees": [[colonne, % manquant]]}}
        """
        return {
            str(d): {
                "bilan": [[etape, int(n)] for etape, n in self.bilans[d]["lignes"].items()],
                "colonnes_retirees": [[c, float(p)] for c, p
                                      in self.colonnes_retirees[d]["pct_manquant"].items()],
            }
            for d in self.bilans
        }


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
            bilan, retirees = [], []
            resultat[departement] = nettoyer(df, bilan, retirees)
            self.bilans[departement] = pd.DataFrame(
                bilan, columns=["etape", "lignes"]).set_index("etape")
            self.colonnes_retirees[departement] = pd.DataFrame(
                retirees, columns=["colonne", "pct_manquant"]).set_index("colonne")
        return resultat
