import json
from dotenv import load_dotenv
load_dotenv('../.env')

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import mongodb_wrappers
import datetime

wrapper = mongodb_wrappers.MongoDBWrapper()

repo_tool_histories = wrapper.get_repo_tool_histories()

repos_active_by_year = {}

for repo_history in repo_tool_histories:
    active_years = set()
    for snapshot in repo_history['snapshots']:
        if snapshot['date'].year < 2012 or snapshot['date'].year > 2022:
            continue
        active_years.add(snapshot['date'].year)

    for active_year in active_years:
        if active_year not in repos_active_by_year:
            repos_active_by_year[active_year] = 0

        repos_active_by_year[active_year] += 1

repos_active_by_year_formatted = []

for year in repos_active_by_year:
    repos_active_by_year_formatted.append({'year' : year, 'number_of_repos' : repos_active_by_year[year]})

with open('repos_active_by_year.json', 'w') as file:
    file.write(json.dumps(repos_active_by_year_formatted, indent=2))