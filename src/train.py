from data.repository import DataRepository
from preprocessing import DataPreprocessor
from models.registry import ModelRegistry


class TrainingPipeline():
    """
    Starting point for the training pipeline. 
    Responsible for orchestrating the training process, 
    including data loading, preprocessing, model training, and evaluation.
    """
    def __init__(self):

        self.__preprocessor:DataPreprocessor = None
        self.__repository:DataRepository = None
        self.__registry:ModelRegistry = None
        tasks_config:dict
        pass

    def run(self, snapid:int)-> dict:
        """
        Run the training pipeline for a given snapshot ID.
        """
        # 1 load data

        # 2 preprocess data

        # 3 train model (snap id)

        # 4 evaluate model (snap id)

        # adapt task config


        pass


if __name__ == "__main__":
    pipeline = TrainingPipeline()
    # Add code to run the training pipeline
    