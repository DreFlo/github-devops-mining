import plotly.graph_objects as go

import csv
import itertools

data_file = open('repo_tools_history.csv', 'r')
data_csvreader = csv.reader(data_file, delimiter=';')

all_tools= set()

next(data_csvreader) # skip sep
header = next(data_csvreader)[1:]

rows = []

while True:
    try:
        row = next(data_csvreader)
    except StopIteration:
        break
    rows.append(row)
    for tools in row[1:]:
        all_tools |= set(tools.split(','))

all_tools.remove('')

all_tools = sorted(list(all_tools))

tool_to_index = {tool: i for i, tool in enumerate(all_tools)}

print(len(header))

number_dif_rows = 0
for row in rows:
    if len(row) != len(header):
        number_dif_rows += 1
    
print(number_dif_rows)
print(len(rows))

# tool_combinations = list(itertools.combinations(all_tools, 2))

# transitions = {i : {tool_comb : 0 for tool_comb in tool_combinations} for i in range(1, len(header) - 1)}

# for row in rows:
#     for i in range(1, len(header) - 1):
#         for (tool1, tool2) in tool_combinations:
#             if tool1 in row[i] and tool2 in row[i + 1]:
#                 transitions[i][(tool1, tool2)] += 1

# fig_dict = dict(
#     source = list(itertools.chain.from_iterable([[tool_to_index[tool1] for (tool1, _) in tool_combs] for tool_combs in transitions.values()])),
#     target = list(itertools.chain.from_iterable([[tool_to_index[tool2] for (_, tool2) in tool_combs] for tool_combs in transitions.values()])),
#     value = list(itertools.chain.from_iterable([list(tool_combs.values()) for tool_combs in transitions.values()])),
# )


# fig = go.Figure(data=[go.Sankey(
#     node = dict(
#       pad = 15,
#       thickness = 20,
#       line = dict(color = "black", width = 0.5),
#       label = all_tools,
#       color = "blue"
#     ),
#     link = fig_dict)
#     ])

# fig.update_layout(title_text="Basic Sankey Diagram", font_size=10)
# fig.show()