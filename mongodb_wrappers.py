import os
import pprint

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.cursor import Cursor
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("MONGODB_URI")

class MongoDBWrapper:
    def __init__(self, uri=URI):
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        self.db = self.client["Repositories"]

    def get_collection(self, collection_name):
        return self.db[collection_name]
    
    def get_all_collections(self) -> list:
        return self.db.list_collection_names()
    
    def get_repositories(self, filter : dict = {}, projection : dict = None) -> Cursor:
        return self.db["random"].find(filter, projection)
    
    def add_tree(self, tree : dict):
        self.db["trees"].insert_one(tree)

    def add_trees(self, trees : list):
        self.db["trees"].insert_many(trees)