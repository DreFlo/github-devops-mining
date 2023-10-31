import json
import statistics
from dotenv import load_dotenv
load_dotenv('../.env')

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import mongodb_wrappers
import datetime

wrapper = mongodb_wrappers.MongoDBWrapper()

repo_tool_histories = wrapper.get_repo_tool_histories()

all_tool_times = {}

for repo_tool_history in repo_tool_histories:
    tool_times = {}

    prev_date = None
    for snapshot in sorted(repo_tool_history['snapshots'], key=lambda snap:snap['date']):
        date = snapshot['date']
        if date.year < 2012 or date.year > 2022:
            continue

        for tool in snapshot['tools']:
            if tool not in tool_times:
                tool_times[tool] = [[date, None]]
            elif tool in tool_times and tool_times[tool][-1][1] == None:
                continue
            elif tool in tool_times and tool_times[tool][-1][1] != None:
                tool_times[tool].append([date, None])

        for tool in tool_times:
            if tool not in snapshot['tools'] and tool_times[tool][-1][1] == None:
                tool_times[tool][-1][1] = prev_date

        prev_date = date


    for tool in tool_times:
        if tool_times[tool][-1][1] == None:
            if tool_times[tool][-1][0] == prev_date:
                tool_times[tool].pop()
            else:
                tool_times[tool][-1][1] = prev_date

        if tool not in all_tool_times:
            all_tool_times[tool] = []

        all_tool_times[tool].extend(tool_times[tool])


tool_periods_data = []

for tool in all_tool_times:
    # For each tool get avg, median, min, max, and std dev
    tool_periods = []
    for period in all_tool_times[tool]:
        tool_periods.append((period[1] - period[0]).days)

    tool_periods_data.append({
        'tool' : tool,
        'avg' : sum(tool_periods) / len(tool_periods) if len(tool_periods) > 0 else None,
        'median' : statistics.median(tool_periods) if len(tool_periods) > 0 else None,
        'min' : min(tool_periods) if len(tool_periods) > 0 else None,
        'max' : max(tool_periods)if len(tool_periods) > 0 else None,
        'std_dev' : statistics.stdev(tool_periods) if len(tool_periods) > 1 else None,
        'use_periods' : len(tool_periods)
    })

with open('tool_periods.json', 'w') as f:
    json.dump(tool_periods_data, f, indent=4)

            