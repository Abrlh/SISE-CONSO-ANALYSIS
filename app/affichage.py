"""Éléments d'affichage partagés par les pages."""

from src.analysis import ETIQUETTES

# Couleurs des étiquettes DPE, de A (vert) à G (rouge), dans le même ordre que ETIQUETTES
COULEURS_ETIQUETTES = ["#319834", "#33cc31", "#cbfc34", "#fbfe06", "#fccc05", "#fc9935", "#fc0205"]


def fmt_nombre(valeur, decimales=0):
    """Met un nombre en forme à la française (386450 -> '386 450'). Renvoie 'n/a' si la valeur est absente."""
    if valeur is None:
        return "n/a"
    return f"{valeur:,.{decimales}f}".replace(",", " ")
