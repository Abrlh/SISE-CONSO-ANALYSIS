from abc import ABC, abstractmethod
import numpy as np
import pandas as pd


class BaseModel(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def train(self, X:pd.DataFrame,Y:pd.Series)->None:
        """ Train the model with the provided features and target values.
        Args:
            X (pd.DataFrame): The input features for training.
            Y (pd.Series): The target values for training.
        """
        pass

    def predict(self, X:pd.DataFrame)-> np.ndarray:
        pass

    def evaluate(self, X:pd.DataFrame, Y:pd.Series)-> dict:
        pass