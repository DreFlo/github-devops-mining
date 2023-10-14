import re
import time
import dateutil.parser

from github_api_wrappers import *
from datetime import datetime, timedelta
from enum import Enum

from tree_collection_loader import *

class DevOpsTechnologies(Enum):
    GITHUB_ACTIONS = 0
    JENKINS = 1
    TRAVIS_CI = 2
    CIRCLE_CI = 3
    GRADLE = 4
    RAKE = 5
    RANCHER = 6
    DOCKER = 7
    PROGRESS_CHEFF = 8
    PUPPET = 9
    NAGIOS = 10
    PROMETHEUS = 11    

# TODO Improve all check funtions, they are probably not very accurate
def check_github_actions(node) -> bool:
    return re.search(r'^\.github\/workflows\/.+\.ya?ml', node['path'])

def check_jenkins(node) -> bool:
    return re.search(r'Jenkinsfile', node['path'])

def check_travis_ci(node) -> bool:
    return re.search(r'\.travis\.ya?ml', node['path'])

def check_circle_ci(node) -> bool:
    return re.search(r'^(circle.ya?ml|\.circleci\/config\.ya?ml)', node['path'])

def check_gradle(node) -> bool:
    return re.search(r'build.gradle', node['path'])

def check_rake(node) -> bool:
    return re.search(r'Rakefile', node['path'])

def check_rancher(node) -> bool:
    return re.search(r'Kube_config_rancher-cluster\.ya?ml', node['path'])

def check_docker(node) -> bool:
    return re.search(r'Dockerfile', node['path'])

def check_progress_cheff(node) -> bool:
    return re.search(r'Metadata\.rb', node['path'])

def check_puppet(node) -> bool:
    return re.search(r'Site\.pp', node['path'])

def check_nagios(node) -> bool:
    return re.search(r'Nagios\.cfg', node['path'])

def check_prometheus(node) -> bool:
    return re.search(r'Prometheus\.ya?ml', node['path'])

def get_devops_technologies(tree : list) -> list:
    technologies = set()
    for node in tree:
        if not DevOpsTechnologies.GITHUB_ACTIONS in technologies and check_github_actions(node):
            technologies.add(DevOpsTechnologies.GITHUB_ACTIONS)
        elif not DevOpsTechnologies.JENKINS in technologies and check_jenkins(node):
            technologies.add(DevOpsTechnologies.JENKINS)
        elif not DevOpsTechnologies.TRAVIS_CI in technologies and check_travis_ci(node):
            technologies.add(DevOpsTechnologies.TRAVIS_CI)
        elif not DevOpsTechnologies.CIRCLE_CI in technologies and check_circle_ci(node):
            technologies.add(DevOpsTechnologies.CIRCLE_CI)
        elif not DevOpsTechnologies.GRADLE in technologies and check_gradle(node):
            technologies.add(DevOpsTechnologies.GRADLE)
        elif not DevOpsTechnologies.RAKE in technologies and check_rake(node):
            technologies.add(DevOpsTechnologies.RAKE)
        elif not DevOpsTechnologies.RANCHER in technologies and check_rancher(node):
            technologies.add(DevOpsTechnologies.RANCHER)
        elif not DevOpsTechnologies.DOCKER in technologies and check_docker(node):
            technologies.add(DevOpsTechnologies.DOCKER)
        elif not DevOpsTechnologies.PROGRESS_CHEFF in technologies and check_progress_cheff(node):
            technologies.add(DevOpsTechnologies.PROGRESS_CHEFF)
        elif not DevOpsTechnologies.PUPPET in technologies and check_puppet(node):
            technologies.add(DevOpsTechnologies.PUPPET)
        elif not DevOpsTechnologies.NAGIOS in technologies and check_nagios(node):
            technologies.add(DevOpsTechnologies.NAGIOS)
        elif not DevOpsTechnologies.PROMETHEUS in technologies and check_prometheus(node):
            technologies.add(DevOpsTechnologies.PROMETHEUS)

    return [technology.name for technology in technologies]

was_interrupted = False

def set_interrupted(_, __):
    global was_interrupted
    was_interrupted = True
    print('Interrupted')

signal.signal(signal.SIGINT, set_interrupted)

parsed_repos = set((repo['full_name'] for repo in json.loads(open('repo_infos.json', 'r').read())) if os.path.exists('repo_infos.json') else [])
print(parsed_repos)

wrapper = MongoDBWrapper()

repos = wrapper.get_repositories(filter={}, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0})

repo_infos = json.loads(open('repo_infos.json', 'r').read()) if os.path.exists('repo_infos.json') else []

for repo in repos:
    if was_interrupted:
        break

    repo_full_name = repo['full_name']

    if repo_full_name in parsed_repos:
        print(f'Skipping {repo_full_name}')
        continue

    print(f'Processing {repo_full_name}')
    
    commit_count = get_commits_count(repo_full_name)

    repo_snapshot_commits = get_snapshot_commits_optimized(
        repo_full_name, 
        commit_count, 
        dateutil.parser.parse(repo['created_at']), 
        dateutil.parser.parse(repo['updated_at']), 
        timedelta(days=90)) # TODO Check interval
    
    repo_snapshot_trees = get_repo_trees(full_name=repo_full_name, commits=repo_snapshot_commits)

    repo_snapshot_devops_technologies = []

    for tree in repo_snapshot_trees:
        if 'tree' in tree:
            repo_snapshot_devops_technologies.append(get_devops_technologies(tree['tree']))
        else:
            repo_snapshot_devops_technologies.append([])

    for i in range(len(repo_snapshot_commits)):
        repo_snapshot_commits[i]['devops_technologies'] = repo_snapshot_devops_technologies[i]

    repo_info = {'full_name': repo_full_name, 'snapshot_commits': repo_snapshot_commits}

    repo_infos.append(repo_info)

    parsed_repos.add(repo_full_name)

    # Store in JSON file
    with open(f'repo_infos.json', 'w') as output_file:
        output_file.write(json.dumps(repo_infos, indent=2))

print('Done')

