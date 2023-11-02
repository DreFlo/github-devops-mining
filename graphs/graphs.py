import json
import sys

from dateutil import parser

tool_histories = None

with open('Repositories.repo_tools_history.json', 'r') as db:
    tool_histories = json.load(db)

snapshot_date = lambda snapshot : snapshot['date']

def get_snapshot_with_datetime(snapshot : dict) -> dict:
    return {
        'sha' : snapshot['sha'],
        'tools' : snapshot['tools'],
        'date' : parser.isoparse(snapshot['date']['$date'])
    }

def get_tools_for_year(snapshots : list[dict], year : int) -> set | None:
    tools = set()

    active_in_year = False

    if snapshots[0]['date'].year > year:
        return None

    for snapshot in snapshots:
        if snapshot['date'].year == year:
            active_in_year = True
            tools |= set(snapshot['tools'])

    # Get most recent snapshot if none found in year
    if not active_in_year:
        for snapshot in snapshots[::-1]:
            if snapshot['date'].year < year:
                # If repo not active since
                if snapshot['sha'] == snapshots[-1]['sha']:
                    return None
                tools |= set(snapshot['tools'])
                break

    return tools

# end inclusive
def group_tool_histories_by_year(tool_histories : dict, start : int, end : int) -> dict:
    tool_histories_by_year = {year : {} for year in range(start, end + 1)}

    for tool_history in tool_histories:
        snapshots_with_datetime = [get_snapshot_with_datetime(snapshot=snapshot) for snapshot in tool_history['snapshots']]
        snapshots_with_datetime = sorted(snapshots_with_datetime, key=snapshot_date)

        for year in range(start, end + 1):
            tools_for_year = get_tools_for_year(snapshots=snapshots_with_datetime, year=year)

            if tools_for_year is not None:
                tool_histories_by_year[year][tool_history['repo_full_name']] = tools_for_year

    return tool_histories_by_year

def get_number_of_repos_with_n_tools(tool_histories_for_year : dict) -> set:
    number_of_repos_grouped_by_number_of_tools = {}

    for repo in tool_histories_for_year:
        number_of_tools = len(tool_histories_for_year[repo])

        if number_of_tools not in number_of_repos_grouped_by_number_of_tools:
            number_of_repos_grouped_by_number_of_tools[number_of_tools] = 0

        number_of_repos_grouped_by_number_of_tools[number_of_tools] += 1

    return number_of_repos_grouped_by_number_of_tools

def get_repos_with_n_tools_graphs(tool_histories_by_year : dict) -> dict:
    repos_with_n_tools = {}

    for year in tool_histories_by_year:
        repos_with_n_tools[year] = get_number_of_repos_with_n_tools(tool_histories_for_year=tool_histories_by_year[year])

    repos_with_n_tools_formatted = {}
    repos_with_n_tools_percentage_formatted = {}

    for year in repos_with_n_tools:
        repos_with_n_tools_formatted[year] = []
        repos_with_n_tools_percentage_formatted[year] = []

        for number_of_tools in repos_with_n_tools[year]:
            repos_with_n_tools_formatted[year].append({'number_of_tools' : number_of_tools, 'number_of_repos' : repos_with_n_tools[year][number_of_tools]})
            repos_with_n_tools_percentage_formatted[year].append({'number_of_tools' : number_of_tools, 'percentage' : repos_with_n_tools[year][number_of_tools] / len(tool_histories_by_year[year]) * 100})

    graphs = {}
    percentage_graphs = {}

    for year in repos_with_n_tools:
        # Vegalite histogram
        graphs[year] = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": {
                "values" : repos_with_n_tools_formatted[year]
            },
            "title" : f"Number of repositories with n tools in {year}",
            "mark": "bar",
            "encoding": {
                "x": {
                    "field": "number_of_tools",
                    "type": "nominal",
                    "title" : "Number of tools"
                },
                "y": {
                    "field": "number_of_repos",
                    "type": "quantitative",
                    "title" : "Number of repositories"
                }
            }
        }

        percentage_graphs[year] = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": {
                "values" : repos_with_n_tools_percentage_formatted[year]
            },
            "title" : f"Distribution of repositories with n tools in {year}",
            "mark": "bar",
            "encoding": {
                "x": {
                    "field": "number_of_tools",
                    "type": "nominal",
                    "title" : "Number of tools"
                },
                "y": {
                    "field": "percentage",
                    "type": "quantitative",
                    "title" : "Percentage"
                }
            }
        }
        
    return graphs, percentage_graphs

def get_tool_counts(tool_histories_for_year : dict) -> dict:
    tool_counts = {}

    for repo in tool_histories_for_year:
        for tool in tool_histories_for_year[repo]:
            if tool not in tool_counts:
                tool_counts[tool] = 0

            tool_counts[tool] += 1

    return tool_counts

def get_tool_counts_percentages_by_year(tool_counts_by_year : dict, tool_histories_by_year : dict) -> dict:
    tool_count_percentages = {}

    number_of_repos_by_year = {year : len(tool_histories_for_year) for year, tool_histories_for_year in tool_histories_by_year.items()}

    for year in tool_counts_by_year:
        tool_count_percentages[year] = {}

        for tool in tool_counts_by_year[year]:
            tool_count_percentages[year][tool] = tool_counts_by_year[year][tool] / number_of_repos_by_year[year] * 100

    return tool_count_percentages

def get_tool_counts_by_year_group_other(tool_counts_by_year : dict, tool_count_percentages_by_year : dict, threshold : float = 1.00) -> dict:
    tool_counts_by_year_group_other = {}

    for year in tool_counts_by_year:
        tool_counts_by_year_group_other[year] = {}

        for tool in tool_counts_by_year[year]:
            if tool_count_percentages_by_year[year][tool] < threshold:
                if f'Other (<{threshold}%)' not in tool_counts_by_year_group_other[year]:
                    tool_counts_by_year_group_other[year][f'Other (<{threshold}%)'] = 0

                tool_counts_by_year_group_other[year][f'Other (<{threshold}%)'] += tool_counts_by_year[year][tool]
            else:
                tool_counts_by_year_group_other[year][tool] = tool_counts_by_year[year][tool]

    return tool_counts_by_year_group_other


def get_tool_counts_stacked_bar_chart(tool_counts_by_year : dict) -> dict:
    stacked_bar_chart = {}

    stacked_bar_chart = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : [{'year' : year, 'tool' : tool, 'count' : tool_counts_by_year[year][tool]} for year in tool_counts_by_year for tool in tool_counts_by_year[year]]
        },
        "title" : "Number of repositories with tool by year",
        "mark": "bar",
        "encoding": {
            "x": { 
                "field": "year",
                "type": "ordinal",
                "title": "Year"
            },
            "y": {
                "field": "count",
                "type": "quantitative",
                "title": "Number of repositories"
            },
                "color": {
                "field": "tool",
                "type": "nominal",
                "title": "Tool"
            }
        }
    }

    return stacked_bar_chart

print('Grouping tool histories by year')
tools_by_year = group_tool_histories_by_year(tool_histories=tool_histories, start=2012, end=2023)

print('Making n tools histograms')
n_tools_histograms, percentage_n_tools_histograms = get_repos_with_n_tools_graphs(tool_histories_by_year=tools_by_year)

for year in n_tools_histograms:
    with open(f'number_of_tools_histograms/{year}.json', 'w') as file:
        file.write(json.dumps(n_tools_histograms[year], indent=2))

for year in percentage_n_tools_histograms:
    with open(f'number_of_tools_histograms/{year}_percentages.json', 'w') as file:
        file.write(json.dumps(percentage_n_tools_histograms[year], indent=2))

print('Getting tool counts')
tool_counts_by_year = {year : get_tool_counts(tool_histories_for_year=tools_by_year[year]) for year in tools_by_year}

tool_count_percentages_by_year = get_tool_counts_percentages_by_year(tool_counts_by_year=tool_counts_by_year, tool_histories_by_year=tools_by_year)

tool_counts_by_year_group_other = get_tool_counts_by_year_group_other(tool_counts_by_year=tool_counts_by_year, tool_count_percentages_by_year=tool_count_percentages_by_year)

print('Making stacked bar chart')
stacked_bar_chart = get_tool_counts_stacked_bar_chart(tool_counts_by_year=tool_counts_by_year_group_other)

with open(f'stacked_bar_chart.json', 'w') as file:
    file.write(json.dumps(stacked_bar_chart, indent=2))
