from .api_client import AdempiereClient
from ..storage import Storage

class DataRepository():
    def __init__(self):
        self.__client:AdempiereClient = None
        self.__storage:Storage = None
        pass