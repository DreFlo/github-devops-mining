from dotenv import load_dotenv
load_dotenv()

import mongodb_wrappers
from datetime import timedelta
import json
from datetime import datetime

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

tool_launch_dates = {
        "Agola" : datetime(2019, 7, 15),
        "AppVeyor" : datetime(2011, 1, 1),
        "ArgoCD" : datetime(2018, 3, 13),
        "Bytebase" : datetime(2021, 7, 9),
        "Cartographer" : datetime(2021, 9, 21),
        "CircleCI" : datetime(2011, 1, 1),
        "Cloud 66 Skycap" : datetime(2017, 12, 7),
        "Cloudbees Codeship" : datetime(2011, 1, 1),
        "Devtron" : datetime(2021, 4, 7),
        "Flipt" : datetime(2019, 2, 16),
        "GitLab" : datetime(2012, 10, 22),
        "Google Cloud Build" : datetime(2016, 1, 14),
        "Helmwave" : datetime(2020, 10, 2),
        "Travis" : datetime(2011, 1, 1),
        "Jenkins" : datetime(2011, 2, 3),
        "JenkinsX" : datetime(2018, 3, 19),
        "Keptn" : datetime(2021, 5, 21),
        "Liquibase" : datetime(2006, 1, 1),
        "Mergify" : datetime(2018, 8, 1),
        "OctopusDeploy" : datetime(2011, 10 ,7),
        "OpenKruise" : datetime(2019, 7, 17),
        "OpsMx" : datetime(2017, 9, 1),
        "Ortelius" : datetime(2023, 2, 13),
        "Screwdriver" : datetime(2017, 1, 12),
        "Semaphore" : datetime(2012, 1, 1),
        "TeamCity" : datetime(2006, 1, 1),
        "werf" : datetime(2017, 8, 22),
        "Woodpecker CI" : datetime(2019, 4, 6),
        "Codefresh" : datetime(2014, 1, 1),
        "XL Deploy" : datetime(2008, 1, 1),
        "Drone" : datetime(2014, 1, 1),
        "Flagger" : datetime(2018, 10, 7),
        "Harness.io" : datetime(2016, 1, 1),
        "Flux" : datetime(2016, 10, 28),
        "GoCD" : datetime(2007, 1, 1),
        "Concourse" : datetime(2015, 1, 27),
        "Kubernetes" : datetime(2014, 10, 15),
        "GitHubActions" : datetime(2018, 10, 16),
        "AWS CodePipeline" : datetime(2015, 7, 9),
    }

bad_repos = 0
total_repos = 0

snapshot_total = 0

for repo in repo_tool_histories_list:
    total_repos += 1
    error = False
    for snap in repo['snapshots']:
        snapshot_total += 1
        for tool in snap['tools']:
            if snap['date'] < tool_launch_dates[tool]:
                count += 1
                error = True
                break
    if error:
        bad_repos += 1

print('Total snapshots:', snapshot_total)
print('Total repos:', total_repos)
print('bad snapshots:', count)
print('Bad repos:', bad_repos)
print(f'Bad snap percentage {count/snapshot_total * 100}%')
print(f'bad repos percentage {bad_repos/total_repos * 100}%')
