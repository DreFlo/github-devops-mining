import json
import plotly.graph_objects as go

import csv
import itertools

data_file = open('repo_tools_history.csv', 'r')
data_csvreader = csv.reader(data_file, delimiter=';')

all_tools= set()

next(data_csvreader) # skip sep
header = next(data_csvreader)

rows = []

while True:
    try:
        row = next(data_csvreader)
    except StopIteration:
        break
    rows.append(row)
    for tools in row[1:]:
        all_tools |= set(tools.split(','))

if '' in all_tools:
    all_tools.remove('')

all_tools = sorted(list(all_tools))

tool_to_index = {tool: i for i, tool in enumerate(all_tools)}    

tool_combinations = list(itertools.permutations(all_tools, 2))
tool_combinations.extend([(tool, tool) for tool in all_tools])

transitions = {i - 1 : {tool_comb : 0 for tool_comb in tool_combinations} for i in range(1, len(header) - 1)}

for row in rows:
    for i in range(1, len(row) - 1):
        if row[i] == row[i + 1] and row[i] != '':
            for tool in row[i].split(','):
                transitions[i-1][(tool, tool)] += 1
        else:
            for (tool1, tool2) in tool_combinations:
                # Changes tool (stop cycles if repo has multiple tools)
                if tool1 in row[i] and tool2 in row[i + 1]:
                    transitions[i-1][(tool1, tool2)] += 1

fig_dict = dict(
    source = list(itertools.chain.from_iterable([[tool_to_index[tool1] + i * len(tool_combinations) for (tool1, _) in tool_combs] for i, tool_combs in transitions.items()])),
    target = list(itertools.chain.from_iterable([[tool_to_index[tool2] + (i + 1) * len(tool_combinations) for (_, tool2) in tool_combs] for i, tool_combs in transitions.items()])),
    value = list(itertools.chain.from_iterable([list(tool_combs.values()) for tool_combs in list(transitions.values())])),
)

# with open('fig_dict.json', 'w') as f:
#     json.dump(fig_dict, f, indent=4)

all_tools_cycle = []

for _ in range(len(transitions.keys()) * 2 * len(tool_combinations)):
    all_tools_cycle.extend(all_tools)

fig = go.Figure(data=[
    go.Sankey(
        node = dict(
        pad = 15,
        thickness = 20,
        line = dict(color = "black", width = 0.5),
        label = all_tools_cycle,
        color = "blue"
        ),
        link = fig_dict,
        domain = dict(x = [0, 1], y = [0, 1])
    )
])

fig.update_layout(title_text="Basic Sankey Diagram", font_size=10)
fig.show()