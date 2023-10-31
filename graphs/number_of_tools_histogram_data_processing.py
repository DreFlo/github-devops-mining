import json
from dotenv import load_dotenv
load_dotenv('../.env')

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import mongodb_wrappers
import datetime

wrapper = mongodb_wrappers.MongoDBWrapper()

repo_tool_histories = wrapper.get_repo_tool_histories()

number_of_tools_by_year = {}

for repo_tool_history in repo_tool_histories:
    tools_by_year = {}
    for snapshot in repo_tool_history['snapshots']:
        date = snapshot['date']
        if date.year < 2012 or date.year > 2022:
            continue
        if date.year not in tools_by_year:
            tools_by_year[date.year] = set()
        tools_by_year[date.year] |= set(snapshot['tools'])

    for year in tools_by_year:
        if year not in number_of_tools_by_year:
            number_of_tools_by_year[year] = {}

        number_of_tools = len(tools_by_year[year])

        if number_of_tools not in number_of_tools_by_year[year]:
            number_of_tools_by_year[year][number_of_tools] = 0

        number_of_tools_by_year[year][number_of_tools] += 1

number_of_tools_by_year_formatted = {}

for year in number_of_tools_by_year:
    if year not in number_of_tools_by_year_formatted:
        number_of_tools_by_year_formatted[year] = []

    for tools_by_year in number_of_tools_by_year[year]:
        number_of_tools_by_year_formatted[year].append({'number_of_tools' : tools_by_year, 'number_of_repos' : number_of_tools_by_year[year][tools_by_year]})

for year in number_of_tools_by_year_formatted:
    vegalite_json = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : number_of_tools_by_year_formatted[year]
        },
        "mark": "bar",
        "encoding": {
            "x": {
            "field": "number_of_tools",
            "type": "nominal"
            },
            "y": {
            "field": "number_of_repos",
            "type": "quantitative"
            }
        }
    }

    with open(f'number_of_tools_histograms/{year}.json', 'w') as file:
        file.write(json.dumps(vegalite_json, indent=2))

        