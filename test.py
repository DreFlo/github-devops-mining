from dotenv import load_dotenv
load_dotenv()

import mongodb_wrappers
from datetime import timedelta
import json

wrapper = mongodb_wrappers.MongoDBWrapper()

count = 0

repo_tool_histories_list = wrapper.get_repo_tool_histories()

# reprocess_repo_names = set()

# for repo in repo_tool_histories_list:
#     for i in range(len(repo['snapshots']) - 1):
#         if repo['snapshots'][i + 1]['date'] - repo['snapshots'][i]['date'] > timedelta(days=2 * 365):
#             reprocess_repo_names.add(repo['repo_full_name'])
#             break


# print(f'{len(reprocess_repo_names)} repos to reprocess')

# with open('repo_to_reprocess.json', 'w') as file:
#     file.write(json.dumps(list(reprocess_repo_names), indent=2))    

# repos_to_reprocess = None

# with open('repo_to_reprocess.json', 'r') as file:
#     repos_to_reprocess = json.loads(file.read())

# print(f'{len(repos_to_reprocess)} repos to reprocess')

# for repo_name in repos_to_reprocess:
#     wrapper.db_2['repo_tools_history'].delete_one({'repo_full_name' : repo_name})
#     wrapper.db['random'].update_one({"full_name" : repo_name}, {"$set" : {"retrieved_repo_histories" : False}})

# print('Done')

for repo in repo_tool_histories_list:
    for snap in repo['snapshots']:
        if 'warning' in snap:
            count += 1

print(count)