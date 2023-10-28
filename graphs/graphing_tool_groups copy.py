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

def read_rows_and_count_tools_by_quarter(csvreader, since_index, until_index):
    tools_by_period = {}
    rows = []

    while True:
        try:
            row = next(csvreader)
        except StopIteration:
            break

        rows.append(row)

        for i in range(since_index, until_index):
            tool_set_string = '+'.join(sorted(row[i].split(',')))

            if tool_set_string == '':
                continue

            if i not in tools_by_period:
                tools_by_period[i] = {}

            if tool_set_string not in tools_by_period[i]:
                tools_by_period[i][tool_set_string] = 0

            tools_by_period[i][tool_set_string] += 1

    return (rows, tools_by_period)

def find_most_popular_tools_by_period(tools_by_period : dict, top : int) -> dict:
    pop_tools_by_period = {}

    for period in sorted(list(tools_by_period.keys())):
        tool_sets = tools_by_period[period]

        pop_tool_sets_list = sorted([(tool_set_string, tool_sets[tool_set_string]) for tool_set_string in tool_sets], key=lambda a : a[1], reverse=True)

        pop_tools = {}

        for tool_set_string, value in pop_tool_sets_list[:top]:
            pop_tools[tool_set_string] = value

        pop_tools['Other'] = None

        pop_tools_by_period[period] = pop_tools

    return pop_tools_by_period

def get_all_tool_sets(pop_tools_by_period : dict) -> list:
    all_tool_sets = set()

    for tool_sets in pop_tools_by_period.values():
        for tool_set in tool_sets.keys():
            all_tool_sets.add(tool_set)

    return sorted(list(all_tool_sets))

def get_tool_set_to_index_map(tool_sets : list) -> dict:
    return {tool : index for index, tool in enumerate(tool_sets)}

def get_tool_set_colors(tool_sets : list) -> list:
    return [f'rgba({random.randint(0, 255)},{random.randint(0, 255)},{random.randint(0, 255)},1)' for _ in tool_sets]

def get_transitions(rows : list, pop_tool_sets : dict, filter_tools_sets : set | None = None) -> dict:
    transitions = {}

    for row in rows:
        for period in sorted(list(pop_tool_sets.keys())):
            if (period + 1) not in pop_tool_sets:
                break

            first_it = period - 1 not in pop_tool_sets

            if row[period] == '':
                continue

            tool_set_1 = set(row[period].split(','))
            tool_set_2 = set(row[period + 1].split(','))

            tool_set_1_string = '+'.join(sorted(tool_set_1))
            tool_set_2_string = '+'.join(sorted(tool_set_2))

            tool_set_union = tool_set_1 | tool_set_2

            if (period, period + 1) not in transitions:
                transitions[(period, period + 1)] = {}

            relevant = True

            # Check if includes filter tools or has come from filter tools
            if filter_tools_sets and first_it and filter_tools_sets.isdisjoint(tool_set_union):
                relevant = False
            elif filter_tools_sets and not first_it and filter_tools_sets.isdisjoint(tool_set_union) and tool_set_1_string not in [second for (_, second) in transitions[(period - 1, period)]]:
                relevant = False

            # Check pop
            tool_set_1_string = tool_set_1_string if relevant and tool_set_1_string in pop_tool_sets[period] else 'Other'
            tool_set_2_string = tool_set_2_string if relevant and tool_set_2_string in pop_tool_sets[period  + 1] else 'Other'

            if (tool_set_1_string, tool_set_2_string) not in transitions[(period, period + 1)]:
                transitions[(period, period + 1)][(tool_set_1_string, tool_set_2_string)] = 0

            transitions[(period, period + 1)][(tool_set_1_string, tool_set_2_string)] += 1

    return transitions

def get_node_dict(pop_tool_sets : dict, tool_set_colors : list, tool_set_to_index : dict) -> (list, list):
    labels = []
    colors = []
    customdata = []

    for period in sorted(list(pop_tool_sets.keys())):
        tools_sets = sorted(list(pop_tool_sets[period].keys()))
        if period - 1 not in pop_tool_sets or period + 1 not in pop_tool_sets:
            labels.extend(tools_sets)
        else:
            previous_tool_sets = sorted(list(pop_tool_sets[period - 1].keys()))
            next_tool_sets = sorted(list(pop_tool_sets[period + 1].keys()))
            for tool_set in tools_sets:
                if tool_set in previous_tool_sets or tool_set in next_tool_sets:
                    labels.append('')
                else:
                    labels.append(tool_set)
        colors.extend([tool_set_colors[tool_set_to_index[tool_set]] for tool_set in tools_sets])
        for tool_set in tools_sets:
            customdata.append(f'{tool_set}<br>Quarter: {header[period]}')

    return dict(
        pad = 15,
        thickness = 20,
        line = dict(color = "black", width = 0.5),
        label = labels,
        color = colors,
        customdata = customdata, 
        hovertemplate = "%{customdata}<br>Value: %{value}<extra></extra>"
    )

def get_fig_dict(pop_tool_sets, transitions):
    fig_source = []
    fig_target = []
    fig_value = []

    baseline = 0

    for period in sorted(list(pop_tool_sets.keys())):
        if (period + 1) not in pop_tool_sets:
            break

        source_tool_sets = sorted(list(pop_tool_sets[period].keys()))
        target_tool_sets = sorted(list(pop_tool_sets[period + 1].keys()))

        for (tool_set_string_source, tool_set_string_target) in transitions[(period, period + 1)]:
            fig_source.append(source_tool_sets.index(tool_set_string_source) + baseline)
            fig_target.append(target_tool_sets.index(tool_set_string_target) + baseline + len(source_tool_sets))
            fig_value.append(transitions[(period, period + 1)][(tool_set_string_source, tool_set_string_target)])

        baseline += len(source_tool_sets)

    return dict(
        source = fig_source,
        target = fig_target,
        value = fig_value
    )

rows, tools_by_period = read_rows_and_count_tools_by_quarter(data_csvreader, since_index, until_index)
pop_tools_by_period = find_most_popular_tools_by_period(tools_by_period, 10)
all_tool_sets = get_all_tool_sets(pop_tools_by_period)
tool_set_to_index = get_tool_set_to_index_map(all_tool_sets)
tool_set_colors = get_tool_set_colors(all_tool_sets)
transitions = get_transitions(rows, pop_tools_by_period)
node_dict = get_node_dict(pop_tools_by_period, tool_set_colors, tool_set_to_index)
fig_dict = get_fig_dict(pop_tools_by_period, transitions)

fig = go.Figure(data=[
    go.Sankey(
        node = node_dict,
        link = fig_dict,
        domain = dict(x = [0, 1], y = [0, 1]),
    )
])

fig.update_layout(title_text="Basic Sankey Diagram", font_size=10)
fig.show()