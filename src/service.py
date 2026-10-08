from data.repository import DataRepository
from analysis import StatisticalAnalyzer
from models.registry import ModelRegistry

class AppService():
    """
    Starting point for the application service.
    Responsible for orchestrating the application logic,
    including data loading, preprocessing, statistical analysis, model info
    """
    
    def __init__(self):
        self.__repository:DataRepository = None
        self.__analyzer:StatisticalAnalyzer = None
        self.__registry:ModelRegistry = None
        pass