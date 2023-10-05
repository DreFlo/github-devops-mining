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
        subtrees = self.split_tree_into_subtrees(tree)
        self.db["trees"].insert_many(subtrees)

    def add_trees(self, trees : list):
        subtrees = []
        for tree in trees:
            subtrees.extend(self.split_tree_into_subtrees(tree))
        self.db["trees"].insert_many(subtrees)

    def split_tree_into_subtrees(self, tree : dict) -> list:
        # Initialize subtrees with the root tree
        subtrees = {'' : {'date' : tree['date'], 'repo_full_name' : tree['repo_full_name'], 'tree' : [], 'sha' : tree['sha'], 'path' : ''}}

        # Add subtrees to the subtrees dictionary
        for subtree in tree['tree']:
            if subtree['type'] == 'tree':
                subtrees[subtree['path']] = {'date' : tree['date'], 'repo_full_name' : tree['repo_full_name'], 'tree' : [], 'sha' : subtree['sha'], 'path' : subtree['path']}

        # Add nodes to the subtrees
        for node in tree['tree']:
            subtree_path = '/'.join(node['path'].split('/')[:-1])

            if subtree_path in subtrees:
                subtrees[subtree_path]['tree'].append(node)

        # Convert the subtrees dictionary to a list and return it
        return list(subtrees.values())
    