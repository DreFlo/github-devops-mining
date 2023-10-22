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
    
    def get_repo_tool_histories(self, filter : dict = {}, projection : dict = None) -> Cursor:
        return self.db["repo_tools_history"].find(filter, projection)
    
    def add_repo_tools(self, repo_tools : dict):
        self.db["repo_tools_history"].insert_one(repo_tools)
        # TODO Uncomment this line when we are ready to mark the repo as processed
        # self.db["random"].update_one({"full_name" : repo_tools["repo_full_name"]}, {"retrieved_repo_histories" : True})

    def count_repo_histories(self):
        return self.db["repo_tools_history"].count_documents({})
    
    def count_repo_snapshots(self, repo_name : str):
        repo_history = self.db['repo_tools_history'].find_one({"repo_full_name": repo_name})
        if repo_history is None:
            return 0
        return len(repo_history['snapshots'])
    
    def has_been_processed(self, repo_name : str):
        return self.db['repo_tools_history'].find_one({"repo_full_name": repo_name}) is not None
    
    def delete_repo_histories(self):
        self.db["repo_tools_history"].delete_many({})

    def get_random_processed_repositories(self,size):
        mycol = self.db["random"]

        match = {"$match":  {"$and" : [{'tools_used' : { "$exists": True, "$ne" : []}}, {"created_at" : { "$lt" : "2020-07-16T00:00:00Z"}}, {"retrieved_repo_histories" : {"$ne" : True}}]}}
        sample = {"$sample": {"size": size}} 

        return list(mycol.aggregate([match, sample]))
    