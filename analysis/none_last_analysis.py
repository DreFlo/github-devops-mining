from dotenv import load_dotenv
load_dotenv('../.env')

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import mongodb_wrappers
import random

wrapper = mongodb_wrappers.MongoDBWrapper()

repos = wrapper.get_repo_tool_histories()

for repo in repos:
    repo['snapshots'] = sorted(repo['snapshots'], key=lambda snapshot : snapshot['date'])

repos_last_snapshot = [{'repo_full_name' : repo['repo_full_name'], 'last_snapshot' : repo['snapshots'][-1]} for repo in repos]

empty_last_snapshots = [repo for repo in repos_last_snapshot if len(repo['last_snapshot']['tools']) == 0]

empty_last_snapshots_no_warning = [repo for repo in empty_last_snapshots if 'warning' not in repo['last_snapshot']]

empty_last_snapshots_warning = [repo for repo in empty_last_snapshots if 'warning' in repo['last_snapshot']]

number_of_empty_last_snapshots = len(empty_last_snapshots)

number_of_empty_last_snapshots_no_warning = len(empty_last_snapshots_no_warning)

number_of_empty_last_snapshots_warning = len(empty_last_snapshots_warning)

print('Empty last snapshots:', number_of_empty_last_snapshots)
print('Empty last snapshots (warning):', number_of_empty_last_snapshots_warning)
print('Empty last snapshot (no warning):', number_of_empty_last_snapshots_no_warning )

random.shuffle(empty_last_snapshots)
random.shuffle(empty_last_snapshots_no_warning)
random.shuffle(empty_last_snapshots_warning)

print('All')

for repo in empty_last_snapshots[:10]:
    print(f'https://github.com/{repo["repo_full_name"]}/tree/{repo["last_snapshot"]["sha"]}')

print()

print('no warning')

for repo in empty_last_snapshots_no_warning[:10]:
    print(f'https://github.com/{repo["repo_full_name"]}/tree/{repo["last_snapshot"]["sha"]}')

print()

print('Warning')

for repo in empty_last_snapshots_warning[:10]:
    print(f'https://github.com/{repo["repo_full_name"]}/tree/{repo["last_snapshot"]["sha"]}')

repo_process_tools = []

for repo in empty_last_snapshots:
    doc = wrapper.db['random'].find_one(filter={'full_name' : repo['repo_full_name']}, projection={'tree'})
    if doc:
        repo_process_tools.append(doc['tree'])

dif_sha = [empty_last_snapshots[i]['repo_full_name'] for i in range(len(empty_last_snapshots)) if empty_last_snapshots[i]['last_snapshot']['sha'] != repo_process_tools[i].split('/')[-1]]

print('Dif sha:', len(dif_sha))

for repo in dif_sha[:10]:
    print(repo)