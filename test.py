from dotenv import load_dotenv
load_dotenv()

import mongodb_wrappers
from datetime import timedelta
import json
from datetime import datetime

wrapper = mongodb_wrappers.MongoDBWrapper()

# repo_list = list(wrapper.get_repositories({'retrieved_repo_histories' : True}, {'full_name' : 1, 'tree' : 1, 'tools_used' : 1, '_id' : 0}))

# print(len(repo_list))

# repo_last_sha_map = {repo['full_name'] : (repo['tree'].split('/')[-1], repo['tools_used']) for repo in repo_list}

# cleaned_histories_last_snapshots = list(wrapper.db_3['clean_tool_histories'].aggregate([{'$project' : {'repo_full_name' : 1, 'lastSnapshot' : { '$arrayElemAt' : ['$snapshots', -1]}}}, {'$match' : {'lastSnapshot.tools' : []}}]))

# count = 0

# with open('file.txt', 'w') as file:
#     for repo in cleaned_histories_last_snapshots:
#         if repo['lastSnapshot']['sha'] != repo_last_sha_map[repo['repo_full_name']][0]:
#             file.write(f'Mismatching last snapshots in {repo["repo_full_name"]}\n')
#             file.write(f'Hugo\'s sha: {repo_last_sha_map[repo["repo_full_name"]][0]}\n')
#             file.write(f'Hugo\' tools: {repo_last_sha_map[repo["repo_full_name"]][1]}\n')
#             file.write(f'Cleaned last sha: {repo["lastSnapshot"]["sha"]}\n')
#             file.write(f'Cleaned last tools: {repo["lastSnapshot"]["tools"]}\n\n')
#             count += 1


# circleci = 0
# circleci_githubactions = 0
# circleci_no_githubactions = 0

# for repo in repo_list:
#     tools_used = set(repo['tools_used'])
#     if 'Travis' in tools_used:
#         circleci += 1
#         if 'GitHubActions' in tools_used:
#             circleci_githubactions += 1
#         else:
#             # print(repo['full_name'])
#             circleci_no_githubactions += 1

# print(f'Travis: {circleci}')
# print(f'Travis with GitHubActions: {circleci_githubactions}')
# print(f'Travis without GitHubActions: {circleci_no_githubactions}')

# Unset cleaned histories
# wrapper.db_2['repo_tools_history'].update_many({}, {'$unset' : {'cleaned' : 1}})
# Delete cleaned histories
# wrapper.db_3['clean_tool_histories'].delete_many({})

# full_names_set = set([repo['repo_full_name'] for repo in wrapper.db_3['clean_tool_histories'].find({}, {'repo_full_name' : 1, '_id' : 0})])

# i = 0
# empty_histories = 0

# for name in full_names_set:
#     history = wrapper.db_3['clean_tool_histories'].find_one({'repo_full_name' : name})
    
#     if len(history['snapshots']) != 0 and wrapper.db_3['dedup_clean_histories'].find_one({'full_name' : name}) is None:
#         wrapper.db_3['dedup_clean_histories'].insert_one(history)
#         i += 1

#         if i % 1000 == 0:
#             print(i)
#     else:
#         empty_histories += 1
#         print(f'Empty history for {name}')

# print(f'Empty histories: {empty_histories}')
# print(f'Inserted histories: {i}')

wrongly_processed = set([repo['full_name'] for repo in wrapper.db['random'].find({"retrieved_repo_histories" : True, "tools_used" : []}, {'full_name' : 1, '_id' : 0})])

wrapper.db['random'].update_many({"retrieved_repo_histories" : True, "tools_used" : []}, {'$unset' : {'retrieved_repo_histories' : 1}})