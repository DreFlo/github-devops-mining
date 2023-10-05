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

    def add_trees(self, trees : list):
        # Insert 1000 subtrees at a time
        for i in range(0, len(trees), 5000):
            self.db["trees"].insert_many(trees[i:i+5000])

    def count_repo_trees(self, repo_full_name : str) -> int:
        return self.db["trees"].count_documents({"repo_full_name" : repo_full_name})
    
    def delete_all_trees(self):
        self.db["trees"].delete_many({})
    