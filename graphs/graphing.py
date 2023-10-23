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

all_tools= set()

next(data_csvreader) # skip sep
header = next(data_csvreader)

since_index = header.index(args.since) if args.since else 1
until_index = header.index(args.until) if args.until else len(header) - 1

rows = []

while True:
    try:
        row = next(data_csvreader)
    except StopIteration:
        break
    rows.append(row)
    for tools in row[since_index:]:
        all_tools |= set(tools.split(','))

if '' in all_tools:
    all_tools.remove('')

all_tools = sorted(list(all_tools))

tool_to_index = {tool: i for i, tool in enumerate(all_tools)}    

tool_combinations = list(itertools.permutations(all_tools, 2))
tool_combinations.extend([(tool, tool) for tool in all_tools])

transitions = {i : {tool_comb : 0 for tool_comb in tool_combinations} for i in range(until_index - since_index)}

all_tools_colors = [f'rgba({random.randint(0, 255)},{random.randint(0, 255)},{random.randint(0, 255)},0.8)' for _ in all_tools]

for row in rows:
    for i in range(since_index, until_index):
        if row[i] == row[i + 1] and row[i] != '':
            for tool in row[i].split(','):
                transitions[i-since_index][(tool, tool)] += 1
        else:
            for (tool1, tool2) in tool_combinations:
                # Changes tool (stop cycles if repo has multiple tools)
                if tool1 in row[i] and tool2 in row[i + 1]:
                    transitions[i-since_index][(tool1, tool2)] += 1

all_tools_cycle = []
all_tools_colors_cycle = []

node_customomdata = [header[i] for i in range(since_index, until_index) for _ in range(len(tool_combinations))]

for i in range(len(transitions.keys()) * 2 * len(tool_combinations)):
    all_tools_cycle.extend(all_tools)
    all_tools_colors_cycle.extend(all_tools_colors)

node_colors = [','.join(tool_color.split(',')[:-1]) + ',1)' for tool_color in all_tools_colors_cycle]

fig_source = list(itertools.chain.from_iterable([[tool_to_index[tool1] + i * len(tool_combinations) for (tool1, _) in tool_combs] for i, tool_combs in transitions.items()]))
fig_target = list(itertools.chain.from_iterable([[tool_to_index[tool2] + (i + 1) * len(tool_combinations) for (_, tool2) in tool_combs] for i, tool_combs in transitions.items()]))
fig_value = list(itertools.chain.from_iterable([list(tool_combs.values()) for tool_combs in list(transitions.values())]))
fig_color = [all_tools_colors_cycle[target_index] for target_index in fig_target]



node_dict = dict(
    pad = 15,
    thickness = 20,
    line = dict(color = "black", width = 0.5),
    label = all_tools_cycle,
    color = node_colors,
    customdata = node_customomdata,
    hovertemplate = "%{label}<br>Quarter: %{customdata}<br>Value: %{value}<extra></extra>"
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