from dotenv import load_dotenv
load_dotenv('../.env')

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import mongodb_wrappers

mongodb_wrappers.URI = os.getenv('MONGODB_URI')

print(mongodb_wrappers.URI)

def get_repo_tool_histories(filter : dict = {}) -> list:
    return list(mongodb_wrappers.MongoDBWrapper().get_repo_tool_histories(filter))

def fill_blanks_with_none(histories : list) -> list:
    filled_histories = []
    for history in histories:
        new_history = {'repo_full_name' : history['repo_full_name'], 'snapshots' : []}
        for snapshot in history['snapshots']:
            new_snapshot = {'date' : snapshot['date'], 'sha' : snapshot['sha']}
            if len(snapshot['tools']) == 0:
                new_snapshot['tools'] = ['None']
            else:
                new_snapshot['tools'] = snapshot['tools']
            new_history['snapshots'].append(new_snapshot)
        filled_histories.append(new_history)
    return filled_histories

def flatten_repo_tool_histories(histories : list) -> list:
    flattened_histories = []
    for history in histories:
        for snapshot in history['snapshots']:
            flattened_histories.append({
                'repo_full_name': history['repo_full_name'],
                'date' : snapshot['date'],
                'tools' : snapshot['tools'],
                'sha' : snapshot['sha']
            })
    return flattened_histories

def aggregate_flattened_repo_tool_histories_by_quarter(flattened_histories : list) -> dict:
    aggregated_histories = {}
    for history in flattened_histories:
        # Get quarter from datetime.datetime object
        quarter = (history['date'].month - 1) // 3 + 1
        key = f'{history["date"].year}Q{quarter}'
        if key not in aggregated_histories:
            aggregated_histories[key] = {}
        if history['repo_full_name'] in aggregated_histories[key]:
            aggregated_histories[key][history['repo_full_name']] |= set(history['tools'])
            if len(aggregated_histories[key][history['repo_full_name']]) != 1 and 'None' in aggregated_histories[key][history['repo_full_name']]:
                aggregated_histories[key][history['repo_full_name']].remove('None')
        else:
            aggregated_histories[key][history['repo_full_name']] = set(history['tools'])
    return aggregated_histories

def get_next_quarter_key(key : str) -> str:
    year, quarter = key.split('Q')
    quarter = int(quarter)
    if quarter == 4:
        return f'{int(year) + 1}Q1'
    return f'{year}Q{quarter + 1}'

# Mutates the aggregated_histories dict
def fill_in_blanks_in_aggregated_histories_keys(aggregated_histories : dict) -> dict:
    sorted_keys = sorted(list(aggregated_histories.keys()))
    print(sorted_keys)
    current_key, next_key, index = sorted_keys[0], sorted_keys[1], 1
    while True:
        if get_next_quarter_key(current_key) != next_key:
            aggregated_histories[get_next_quarter_key(current_key)] = {}
            current_key = get_next_quarter_key(current_key)
        else:
            current_key = sorted_keys[index]
            index += 1
            if index == len(sorted_keys):
                break
            next_key = sorted_keys[index]
    return aggregated_histories

# Mutates the aggregated_histories dict
def fill_in_blanks_in_aggregated_histories_values(aggregated_histories : dict) -> dict:
    sorted_keys = sorted(list(aggregated_histories.keys()))
    for i in range(len(sorted_keys) - 1):
        key = sorted_keys[i]
        next_key = sorted_keys[i + 1]
        for repo in aggregated_histories[key]:
            if repo not in aggregated_histories[next_key]:
                aggregated_histories[next_key][repo] = aggregated_histories[key][repo]
    return aggregated_histories

def create_csv_from_aggregate_histories(repos : list, aggregated_histories : dict, filename : str):
    with open(filename, 'w') as f:
        #Sep
        f.write('sep=;\n')
        #Header
        f.write('repo')
        for key in sorted(aggregated_histories.keys()):
            f.write(f';{key}')
        f.write('\n')
        #Data
        for repo in repos:
            f.write(repo)
            for key in sorted(aggregated_histories.keys()):
                if repo in aggregated_histories[key]:
                    f.write(f';{",".join(aggregated_histories[key][repo])}')
                else:
                    f.write(';')
            f.write('\n')


tool_histories = get_repo_tool_histories()
print(len(tool_histories))
filled_histories = fill_blanks_with_none(tool_histories)
flattened_histories = flatten_repo_tool_histories(filled_histories)
aggregated_histories = aggregate_flattened_repo_tool_histories_by_quarter(flattened_histories)
aggregated_histories = fill_in_blanks_in_aggregated_histories_keys(aggregated_histories)
aggregated_histories = fill_in_blanks_in_aggregated_histories_values(aggregated_histories)

repos = [history['repo_full_name'] for history in tool_histories]

create_csv_from_aggregate_histories(repos, aggregated_histories, 'repo_tools_history.csv')
