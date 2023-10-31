import json
from dotenv import load_dotenv
load_dotenv('../.env')

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import mongodb_wrappers
import datetime

wrapper = mongodb_wrappers.MongoDBWrapper()

repo_tool_histories = wrapper.get_repo_tool_histories()

transitions_by_year = {}

for repo_history in repo_tool_histories:
    sorted_snapshots = sorted(repo_history['snapshots'], key=lambda snap:snap['date'])

    for i in range(len(sorted_snapshots) - 1):
        snap_1 = sorted_snapshots[i]
        snap_2 = sorted_snapshots[i + 1]

        if snap_1['date'].year < 2012 or snap_2['date'].year > 2023:
            continue

        if snap_2['date'].year not in transitions_by_year:
            transitions_by_year[snap_2['date'].year] = {'Total transitions' : 0, 'Total changes' : 0}

        transitions_by_year[snap_2['date'].year]['Total transitions'] += 1

        if set(snap_1['tools']) != set(snap_2['tools']):
            transitions_by_year[snap_2['date'].year]['Total changes'] += 1

        for tool in snap_1['tools']:
            if tool not in transitions_by_year[snap_2['date'].year]:
                transitions_by_year[snap_2['date'].year][tool] = {'In' : 0, 'Out' : 0}

            if tool not in snap_2['tools']:
                transitions_by_year[snap_2['date'].year][tool]['Out'] += 1

        for tool in snap_2['tools']:
            if tool not in transitions_by_year[snap_2['date'].year]:
                transitions_by_year[snap_2['date'].year][tool] = {'In' : 0, 'Out' : 0}

            if tool not in snap_1['tools']:
                transitions_by_year[snap_2['date'].year][tool]['In'] += 1

transitions_by_year_formatted = []

for year in transitions_by_year:
    transitions_by_year_formatted.append({'year' : year, 'Total transitions' : transitions_by_year[year]['Total transitions'], 'Total changes' : transitions_by_year[year]['Total changes'], 'Changes percentage' : transitions_by_year[year]['Total changes'] / transitions_by_year[year]['Total transitions']})

    for tool in transitions_by_year[year]:
        if tool == 'Total transitions' or tool == 'Total changes':
            continue

        transitions_by_year_formatted[-1][tool] = transitions_by_year[year][tool]

with open(f'transitions_by_year.json', 'w') as file:
    file.write(json.dumps(transitions_by_year_formatted, indent=2))
        