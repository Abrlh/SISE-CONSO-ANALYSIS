from typing import Any
from .base import BaseModel


class ModelRegistry():
    """
    A registry to save, load and get information about model used
    """


    def __init__(self):
        pass

    def save(model: BaseModel, metadata: Any)-> str:
        pass

    def load()-> BaseModel:
        pass

