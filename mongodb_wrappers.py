import os
import pprint

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.cursor import Cursor

URI = os.getenv("MONGODB_URI")
URI_2 = os.getenv("MONGODB_URI_2")

class MongoDBWrapper:
    def __init__(self, uri=URI):
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        self.db = self.client["Repositories"]

        self.client_2 = MongoClient(URI_2, server_api=ServerApi('1'))
        self.db_2 = self.client_2["Repositories"]

        self.client_3 = MongoClient('mongodb://localhost:27017/', server_api=ServerApi('1'))
        self.db_3 = self.client_3['Repositories']

    def get_collection(self, collection_name):
        return self.db[collection_name]
    
    def get_all_collections(self) -> list:
        return self.db.list_collection_names()
    
    def get_repositories(self, filter : dict = {}, projection : dict = None) -> Cursor:
        return self.db["random"].find(filter, projection)
    
    def get_repo_tool_histories(self, filter : dict = {}, projection : dict = None) -> list:
        return list(self.db_2["repo_tools_history"].find(filter, projection))
    
    def add_repo_tools(self, repo_tools : dict):
        self.db_2["repo_tools_history"].insert_one(repo_tools)
        # TODO Uncomment this line when we are ready to mark the repo as processed
        self.db["random"].update_one({"full_name" : repo_tools["repo_full_name"]}, {"$set" : {"retrieved_repo_histories" : True}})

    def count_repo_histories(self):
        return self.db["repo_tools_history"].count_documents({})
    
    def count_repo_snapshots(self, repo_name : str):
        repo_history = self.db_2['repo_tools_history'].find_one({"repo_full_name": repo_name})
        if repo_history is None:
            return 0
        return len(repo_history['snapshots'])
    
    def has_been_processed(self, repo_name : str):
        return self.db_2['repo_tools_history'].find_one({"repo_full_name": repo_name}) is not None
    
    def delete_repo_histories(self):
        self.db_2["repo_tools_history"].delete_many({})

    def get_random_processed_repositories(self,size):
        mycol = self.db["random"]

        match = {"$match":  {"$and" : [{'tools_used' : { "$exists": True, "$ne" : []}}, {"created_at" : { "$lt" : "2020-07-16T00:00:00Z"}}, {"retrieved_repo_histories" : {"$ne" : True}}]}}
        sample = {"$sample": {"size": size}} 

        return list(mycol.aggregate([match, sample]))
    
    def add_clean_repo_history(self, clean_history):
        self.db_3['clean_tool_histories'].insert_one(clean_history)
        #self.db_2['repo_tools_history'].update_one({'repo_full_name' : clean_history['repo_full_name']}, {'$set' : {'cleaned' : True}})
    
    def get_random_uncleaned_histories(self, size):
        mycol = self.db_2["repo_tools_history"]

        match = {"$match":  {'$and' : [{'cleaned' : {'$ne' : True}}]}}
        sample = {"$sample": {"size": size}} 

        return list(mycol.aggregate([match, sample]))
    
    def has_been_cleaned(self, repo_name):
        return self.db_3['clean_tool_histories'].find_one({"repo_full_name": repo_name}) is not None