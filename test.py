from dotenv import load_dotenv
load_dotenv()

import mongodb_wrappers
from datetime import timedelta
import json
from datetime import datetime

wrapper = mongodb_wrappers.MongoDBWrapper()

repo_list = list(wrapper.get_repositories({'retrieved_repo_histories' : True}, {'full_name' : 1, 'tree' : 1, 'tools_used' : 1, '_id' : 0}))

print(len(repo_list))

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
#     if 'CircleCI' in tools_used:
#         circleci += 1
#         if 'GitHubActions' in tools_used:
#             circleci_githubactions += 1
#             print(repo['full_name'])
#             break
#         else:
#             # print(repo['full_name'])
#             circleci_no_githubactions += 1

# print(f'CircleCI: {circleci}')
# print(f'CircleCI with GitHubActions: {circleci_githubactions}')
# print(f'CircleCI without GitHubActions: {circleci_no_githubactions}')

# Unset cleaned histories
wrapper.db_2['repo_tools_history'].update_many({}, {'$unset' : {'cleaned' : 1}})
# Delete cleaned histories
wrapper.db_3['clean_tool_histories'].delete_many({})