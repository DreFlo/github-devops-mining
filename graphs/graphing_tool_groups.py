import plotly.graph_objects as go

import csv
import itertools
import random
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--file', type=str, default='repo_tools_history.csv', help='File to read from')
parser.add_argument('--since', type=str, nargs='?', help='Since quarter (ex: 2020Q1)')
parser.add_argument('--until', type=str, nargs='?', help='Until quarter (ex: 2020Q2)')
parser.add_argument('--min-stars', type=int, nargs='?', help='Minimum number of stars')
args = parser.parse_args()

data_file = open(args.file, 'r')
data_csvreader = csv.reader(data_file, delimiter=';')

next(data_csvreader) # skip sep
header = next(data_csvreader)

since_index = header.index(args.since) if args.since else 1
until_index = header.index(args.until) + 1 if args.until else len(header) # exclusive

tools_by_quarter = {}

rows = []

while True:
    try:
        row = next(data_csvreader)
    except StopIteration:
        break
    rows.append(row)
    for i in range(since_index, until_index):
        tool_set_string = '+'.join(sorted(row[i].split(',')))
        if not i in tools_by_quarter:
            tools_by_quarter[i] = {}
        if not tool_set_string in tools_by_quarter[i]:
            tools_by_quarter[i][tool_set_string] = 0
        tools_by_quarter[i][tool_set_string] += 1

print("Aggregated tools by quarter")

popular_tools_by_quarter = {}

for i in tools_by_quarter:
    tool_sets = tools_by_quarter[i]
    popular_tool_sets_list = sorted([(key, tool_sets[key]) for key in tool_sets if key != ''], key=lambda a : a[1], reverse=True)
    popular_tool_sets = {}
    for tool_set_string, value in popular_tool_sets_list[:10]:
        popular_tool_sets[tool_set_string] = value
    popular_tools_by_quarter[i] = popular_tool_sets

print("Found most popular tools by quarter")

all_tool_sets = sorted(list(set([tool_set for i in popular_tools_by_quarter for tool_set in popular_tools_by_quarter[i]])))

tool_set_to_index = {tool: i for i, tool in enumerate(all_tool_sets)}    

tool_set_combinations = list(itertools.permutations(tool_set_to_index, 2))
tool_set_combinations.extend([(tool, tool) for tool in tool_set_to_index])

transitions = {i : {tool_comb : 0 for tool_comb in tool_set_combinations} for i in range(until_index - since_index)}

all_tool_sets_colors = [f'rgba({random.randint(0, 255)},{random.randint(0, 255)},{random.randint(0, 255)},0.8)' for _ in all_tool_sets]

print("Calculated combinations")

filter_tool = 'Travis'

for row in rows:
    for i in range(since_index, until_index - 1):
        tool_set_1 = row[i].split(',')
        tool_set_2 = row[i + 1].split(',')

        tool_set_1_string = '+'.join(sorted(tool_set_1))
        tool_set_2_string = '+'.join(sorted(tool_set_2))

        if i == since_index and filter_tool not in tool_set_1 + tool_set_2:
            continue
        elif filter_tool not in tool_set_1 + tool_set_2 and tool_set_1_string not in [second for (_, second) in transitions[i - since_index - 1].keys()]:
            continue

        if tool_set_1_string not in popular_tools_by_quarter[i] or tool_set_2_string not in popular_tools_by_quarter[i + 1]:
            continue

        transitions[i-since_index][(tool_set_1_string, tool_set_2_string)] += 1

print("Added transitions")

all_tool_sets_cycle = []
all_tool_sets_colors_cycle = []

node_customomdata = [header[i] for i in range(since_index, until_index) for (_, _) in tool_set_combinations]


for i in range((len(transitions.keys()) + 1) * len(tool_set_combinations)):
    all_tool_sets_cycle.extend(all_tool_sets)
    all_tool_sets_colors_cycle.extend(all_tool_sets_colors)

node_colors = [','.join(tool_color.split(',')[:-1]) + ',1)' for tool_color in all_tool_sets_colors_cycle]

fig_source = list(itertools.chain.from_iterable([[tool_set_to_index[tool1] + i * len(tool_set_combinations) for (tool1, _) in tool_combs] for i, tool_combs in transitions.items()]))
fig_target = list(itertools.chain.from_iterable([[tool_set_to_index[tool2] + (i + 1) * len(tool_set_combinations) for (_, tool2) in tool_combs] for i, tool_combs in transitions.items()]))
fig_value = list(itertools.chain.from_iterable([list(tool_combs.values()) for tool_combs in list(transitions.values())]))
fig_color = [all_tool_sets_colors_cycle[target_index] for target_index in fig_target]



node_dict = dict(
    pad = 15,
    thickness = 20,
    line = dict(color = "black", width = 0.5),
    label = all_tool_sets_cycle,
    color = node_colors,
    customdata = node_customomdata,
    hovertemplate = "<br>Quarter: %{customdata}<br>Value: %{value}<extra></extra>"
)

fig_dict = dict(
    source = fig_source,
    target = fig_target,
    value = fig_value,
    color = fig_color
)

fig = go.Figure(data=[
    go.Sankey(
        node = node_dict,
        link = fig_dict,
        domain = dict(x = [0, 1], y = [0, 1])
    )
])

fig.update_layout(title_text="Basic Sankey Diagram", font_size=10)
fig.show()