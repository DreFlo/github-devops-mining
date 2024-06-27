import json
import sys

from dateutil import parser
import dateutil

import plotly.graph_objects as go
import plotly.offline as pyo

tool_histories = None

filename = 'Repositories.dedup_clean_histories.json'

colors = [
    "#90abc0",
    "#a12b42",
    "#cd7ff4",
    "#3ad646",
    "#fff2c9",
    "#251981",
    "#4f0b5e",
    "#46de1a",
    "#cdd239",
    "#50bbc8",
    "#9f3a7a",
    "#90c81b",
    "#1c25ce",
    "#055155",
    "#e62777",
    "#2a8bed",
    "#ecadda",
    "#a2c174",
    "#ed8857",
    "#f4ffaa",
    "#98c8d5"
]

with open(filename, 'r') as db:
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

    if len(snapshots) == 0 or snapshots[0]['date'].year > year:
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

def get_max_tools_for_year(snapshots : list[dict], year : int) -> set | None:
    tools = set()

    active_in_year = False

    if len(snapshots) == 0 or snapshots[0]['date'].year > year:
        return None

    for snapshot in snapshots:
        if snapshot['date'].year == year:
            active_in_year = True
            if len(snapshot['tools']) > len(tools):
                tools = set(snapshot['tools'])

    # Get most recent snapshot if none found in year
    if not active_in_year:
        for snapshot in snapshots[::-1]:
            if snapshot['date'].year < year:
                # If repo not active since
                if snapshot['sha'] == snapshots[-1]['sha']:
                    return None
                if len(snapshot['tools']) > len(tools):
                    tools = set(snapshot['tools'])
                break

    return tools

# end inclusive
def group_tool_histories_by_year(tool_histories : dict, start : int, end : int, repo_set : set = None, get_tools_func = get_tools_for_year) -> dict:
    tool_histories_by_year = {year : {} for year in range(start, end + 1)}

    for tool_history in tool_histories:
        if repo_set is not None and tool_history['repo_full_name'] not in repo_set:
            continue

        snapshots_with_datetime = [get_snapshot_with_datetime(snapshot=snapshot) for snapshot in tool_history['snapshots']]
        snapshots_with_datetime = sorted(snapshots_with_datetime, key=snapshot_date)

        for year in range(start, end + 1):
            tools_for_year = get_tools_func(snapshots=snapshots_with_datetime, year=year)

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

def get_repos_with_n_tools_histograms(tool_histories_by_year : dict) -> dict:
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
            "mark": "bar",
            "encoding": {
                "x": {
                    "field": "number_of_tools",
                    "type": "nominal",
                    "title" : "# of tools"
                },
                "y": {
                    "field": "number_of_repos",
                    "type": "quantitative",
                    "title" : "# of repositories"
                }
            }
        }

        percentage_graphs[year] = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": {
                "values" : repos_with_n_tools_percentage_formatted[year]
            },
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

def get_repos_with_n_tools_stacked_bar(tool_histories_by_year : dict) -> dict:
    repos_with_n_tools = {}
    repost_with_n_tools_percentage = {}

    for year in tool_histories_by_year:
        repos_with_n_tools[year] = get_number_of_repos_with_n_tools(tool_histories_for_year=tool_histories_by_year[year])

        repost_with_n_tools_percentage[year] = {}

        for number_of_tools in repos_with_n_tools[year]:
            repost_with_n_tools_percentage[year][number_of_tools] = repos_with_n_tools[year][number_of_tools] / len(tool_histories_by_year[year]) * 100

    graph = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : [{'year' : year, 'number_of_tools' : number_of_tools, 'number_of_repos' : repos_with_n_tools[year][number_of_tools]} for year in repos_with_n_tools for number_of_tools in repos_with_n_tools[year]]
        },
        "mark": "bar",
        "encoding": {
            "x": {
                "field": "year",
                "type": "ordinal",
                "title" : "Year"
            },
            "y": {
                "field": "number_of_repos",
                "type": "quantitative",
                "title" : "# of repos"
            },
            "color": {
                "field": "number_of_tools",
                "type": "nominal",
                "title": "# of technologies",
                "scale": {
                    "range": colors
                }
            }
        }
    }

    percentage_graph = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : [{'year' : year, 'number_of_tools' : number_of_tools, 'percentage' : repost_with_n_tools_percentage[year][number_of_tools]} for year in repost_with_n_tools_percentage for number_of_tools in repost_with_n_tools_percentage[year]]
        },
        "mark": "bar",
        "encoding": {
            "x": {
                "field": "year",
                "type": "ordinal",
                "title" : "Year"
            },
            "y": {
                "field": "percentage",
                "type": "quantitative",
                "title" : "Percentage"
            },
            "color": {
                "field": "number_of_tools",
                "type": "nominal",
                "title": "# of technologies",
                "scale": {
                    "range": colors
                }
            }
        }
    }

    return graph, percentage_graph

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
                "title": "# of repositories"
            },
            "color": {
                "field": "tool",
                "type": "nominal",
                "title": "Technology",
                "scale": {
                    "range": colors
                }
            }
        }
    }

    return stacked_bar_chart

def get_tool_transitions_by_year(tool_histories : dict, ignore_first_if_no_tools : dict, repo_set : set = None) -> dict:
    tool_transitions_by_year = {}

    for tool_history in tool_histories:
        if repo_set is not None and tool_history['repo_full_name'] not in repo_set:
            continue

        snapshots_with_datetime = [get_snapshot_with_datetime(snapshot=snapshot) for snapshot in tool_history['snapshots']]
        snapshots_with_datetime = sorted(snapshots_with_datetime, key=snapshot_date)

        if len(snapshots_with_datetime) == 0:
            continue

        while ignore_first_if_no_tools and len(snapshots_with_datetime[0]['tools']) == 0:
            if len(snapshots_with_datetime) == 1:
                break
            snapshots_with_datetime = snapshots_with_datetime[1:]

        for i in range(len(snapshots_with_datetime) - 1):
            snapshot_1 = snapshots_with_datetime[i]
            snapshot_2 = snapshots_with_datetime[i + 1]

            if snapshot_2['date'].year not in tool_transitions_by_year:
                tool_transitions_by_year[snapshot_2['date'].year] = {'Total transitions' : 0, 'Total changes' : 0}

            tool_transitions_by_year[snapshot_2['date'].year]['Total transitions'] += 1

            if set(snapshot_1['tools']) != set(snapshot_2['tools']):
                tool_transitions_by_year[snapshot_2['date'].year]['Total changes'] += 1

            for tool in snapshot_1['tools']:
                if tool not in tool_transitions_by_year[snapshot_2['date'].year]:
                    tool_transitions_by_year[snapshot_2['date'].year][tool] = {'In' : 0, 'Out' : 0}

                if tool not in snapshot_2['tools']:
                    tool_transitions_by_year[snapshot_2['date'].year][tool]['Out'] += 1

            for tool in snapshot_2['tools']:
                if tool not in tool_transitions_by_year[snapshot_2['date'].year]:
                    tool_transitions_by_year[snapshot_2['date'].year][tool] = {'In' : 0, 'Out' : 0}

                if tool not in snapshot_1['tools']:
                    tool_transitions_by_year[snapshot_2['date'].year][tool]['In'] += 1

    # Add change percentage each year
    for year in tool_transitions_by_year:
        tool_transitions_by_year[year]['Changes percentage'] = tool_transitions_by_year[year]['Total changes'] / tool_transitions_by_year[year]['Total transitions'] * 100

    return tool_transitions_by_year

def get_tool_changes_percentage_graph(tool_transitions_by_year : dict, active_repo_streak : tuple[int, int] = None, repo_set : set = None) -> dict:
    graph = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : [{'year' : year, 'changes_percentage' : tool_transitions_by_year[year]['Changes percentage']} for year in tool_transitions_by_year]
        },
        "layer" : [
            {
                "mark": "bar"
            },
            {
                "mark": {
                    "type": "text",
                    "align": "center",
                    "baseline": "middle",
                    "dx": 15,
                    "angle": 90,
                    "color" : "white"
                },
                "encoding": {
                    "text": {
                        "field": "changes_percentage",
                        "type": "quantitative",
                        "format" : ".2f"
                    }
                }
            }
        ],
        "encoding": {
            "x": { 
                "field": "year",
                "type": "ordinal",
                "title": "Year"
            },
            "y": {
                "field": "changes_percentage",
                "type": "quantitative",
                "title": "Percentage of snapshots"
            }
        }
    }

    return graph

def get_individual_tool_change_by_year_graph(tool_transitions_by_year : dict, tool : str) -> dict:
    values = []

    for year in tool_transitions_by_year:
        if tool in tool_transitions_by_year[year]:
            values.append(
                {
                    'year' : year,
                    'amount' : tool_transitions_by_year[year][tool]['In'],
                    'type' : 'In'
                }
            )

            values.append(
                {
                    'year' : year,
                    'amount' : -tool_transitions_by_year[year][tool]['Out'],
                    'type' : 'Out'
                }
            )

    graph = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : values
        },
        "mark": "bar",
        "encoding": {
            "x": { 
                "field": "year",
                "type": "ordinal",
                "title": "Year"
            },
            "y": {
                "field": "amount",
                "type": "quantitative",
                "title": "# of snapshots",
            },
            "color": {
                "field": "type",
                "type": "nominal",
                "title": "Type of change",
                "scale": {
                    "domain": ["In", "Out"],
                    "range": ["#008000", "#FF0000"]
                }
            }
        }
    }

    return graph

def get_repo_activity_streaks(tool_histories_by_year : dict, start : int, end : int):
    repo_activity_streaks = {}

    for year in range(start, end + 1):
        for repo in tool_histories_by_year[year]:
            if repo not in repo_activity_streaks:
                repo_activity_streaks[repo] = (year, None)

            if year == end or repo not in tool_histories_by_year[year + 1]:
                repo_activity_streaks[repo] = (repo_activity_streaks[repo][0], year)

    return repo_activity_streaks

def get_streak_repos(streaks : dict, start : int, end : int) -> dict:
    streak_sizes = {}

    for streak_start in range(start, end + 1):
        for streak_end in range(streak_start, end + 1):
            streak_sizes[(streak_start, streak_end)] = set()

    for repo in streaks:
        streak_sizes[streaks[repo]].add(repo)

    return streak_sizes

def get_repos_using_tool(tools_for_year : dict, tools : str | list, no_tools : str | list | None = None, repo_set : set = None) -> set:
    repos_using_tool = set()

    if type(tools) == str:
        tools = [tools]
    if no_tools is not None and type(no_tools) == str and no_tools != 'EXCLUDE_ALL_OTHER_TOOLS':
        no_tools = [no_tools]

    tools = set(tools)

    if no_tools is not None and no_tools != 'EXCLUDE_ALL_OTHER_TOOLS':
        no_tools = set(no_tools)

    for repo in tools_for_year:
        if repo_set is not None and repo not in repo_set:
            continue

        if no_tools != 'EXCLUDE_ALL_OTHER_TOOLS':
            if tools.issubset(tools_for_year[repo]):
                if no_tools is None or len(no_tools.intersection(tools_for_year[repo])) == 0:
                    repos_using_tool.add(repo)
        else:
            if tools == tools_for_year[repo]:
                repos_using_tool.add(repo)

    return repos_using_tool

def get_snapshots_by_year(tool_histories : dict, start : int, end : int) -> dict:
    snapshots_by_year = {year : [] for year in range(start, end + 1)}

    for tool_history in tool_histories:
        snapshots_with_datetime = [get_snapshot_with_datetime(snapshot=snapshot) for snapshot in tool_history['snapshots']]
        snapshots_with_datetime = sorted(snapshots_with_datetime, key=snapshot_date)

        for snapshot in snapshots_with_datetime:
            if snapshot['date'].year >= start and snapshot['date'].year <= end:
                snapshots_by_year[snapshot['date'].year].append(snapshot)

    return snapshots_by_year

def get_snapshots_tool_counts_by_year(snapshots_by_year : dict) -> dict:
    snapshots_tool_counts_by_year = {}

    for year in snapshots_by_year:
        snapshots_tool_counts_by_year[year] = {}

        for snapshot in snapshots_by_year[year]:
            if len(snapshot['tools']) not in snapshots_tool_counts_by_year[year]:
                snapshots_tool_counts_by_year[year][len(snapshot['tools'])] = 0

            snapshots_tool_counts_by_year[year][len(snapshot['tools'])] += 1

    return snapshots_tool_counts_by_year

def get_snapshots_tool_counts_graph(snapshots_tool_counts_by_year : dict) -> dict:
    graph = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : [{'year' : year, 'number_of_tools' : number_of_tools, 'number_of_snapshots' : snapshots_tool_counts_by_year[year][number_of_tools]} for year in snapshots_tool_counts_by_year for number_of_tools in snapshots_tool_counts_by_year[year]]
        },
        "mark": "bar",
        "encoding": {
            "x": {
                "field": "year",
                "type": "nominal",
                "title" : "Year"
            },
            "y": {
                "field": "number_of_snapshots",
                "type": "quantitative",
                "title" : "# of snapshots"
            },
            "color": {
                "field": "number_of_tools",
                "type": "nominal",
                "title": "# of tools",
                "scale": {
                    "range": colors
                }
            }
        }
    }

    return graph

def get_time_to_first_tool(tool_histories : dict) -> dict:
    time_to_first_tool = {}

    for tool_history in tool_histories:
        snapshots_with_datetime = [get_snapshot_with_datetime(snapshot=snapshot) for snapshot in tool_history['snapshots']]
        snapshots_with_datetime = sorted(snapshots_with_datetime, key=snapshot_date)

        if len(snapshots_with_datetime) == 0:
            continue

        for i in range(len(snapshots_with_datetime)):
            snapshot = snapshots_with_datetime[i]

            if len(snapshot['tools']) > 0:
                if tool_history['repo_full_name'] not in time_to_first_tool:
                    time_to_first_tool[tool_history['repo_full_name']] = (snapshot['date'] - snapshots_with_datetime[0]['date']).days

                break

    return time_to_first_tool

def get_repos_created_in_year() -> set:
    from dotenv import load_dotenv
    load_dotenv('../.env')

    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import mongodb_wrappers

    wrapper = mongodb_wrappers.MongoDBWrapper()

    repos_created_in_year = {}

    repos = wrapper.get_repositories(filter={'retrieved_repo_histories' : True}, projection={'full_name', 'created_at'})

    for repo in repos:
        year = dateutil.parser.isoparse(repo['created_at']).year

        if year not in repos_created_in_year:
            repos_created_in_year[year] = set()

        repos_created_in_year[year].add(repo['full_name'])

    return repos_created_in_year

def get_mean_time_to_first_tool_by_year(repos_created_by_year : dict, time_to_first_tool : dict) -> dict:
    repos_created_by_year_with_time_to_first_tool = {}

    for year in repos_created_by_year:
        if year < 2012 or year > 2023:
            continue

        repos_created_by_year_with_time_to_first_tool[year] = {}

        for repo in repos_created_by_year[year]:
            if repo in time_to_first_tool:
                repos_created_by_year_with_time_to_first_tool[year][repo] = time_to_first_tool[repo]

    sorted_time_to_first_tool = {}

    for year in repos_created_by_year_with_time_to_first_tool:
        sorted_time_to_first_tool[year] = sorted(repos_created_by_year_with_time_to_first_tool[year].values())

    mean_time_to_first_tool = {}

    for year in sorted_time_to_first_tool:
        mean_time_to_first_tool[year] = sorted_time_to_first_tool[year][len(sorted_time_to_first_tool[year]) // 2]

    return mean_time_to_first_tool

def get_mean_time_to_first_tool_graph(mean_time_to_first_tool : dict) -> dict:
    graph = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : [{'year' : year, 'mean_time_to_first_tool' : mean_time_to_first_tool[year]} for year in mean_time_to_first_tool]
        },
        "layer" : [
            {
                "mark": "bar"
            },
            {
                "mark": {
                    "type": "text",
                    "align": "center",
                    "baseline": "middle",
                    "dx" : 15,
                    "angle": 90,
                    "color" : "white"
                }, 
                "encoding": {
                    "text": {"field": "mean_time_to_first_tool", "type": "quantitative"}
                }
            }
        ],
        "encoding": {
            "x": {
                "field": "year",
                "type": "nominal",
                "title" : "Year of repository creation"
            },
            "y": {
                "field": "mean_time_to_first_tool",
                "type": "quantitative",
                "title" : "Mean time to first technology (days)"
            }
        }
    }

    return graph

def get_transitions(initial_state : str, initial_set : set, final_state : dict, start : int, end : int) -> dict:
    transitions = {}

    for repo in initial_set:
        key = (f'{initial_state} ({start})', f'{final_state[repo]} ({end})') if repo in final_state else (f'{initial_state} ({start})', f'Inactive ({end})')

        if key not in transitions:
            transitions[key] = 0

        transitions[key] += 1

    # Get ten most common transitions other than to inactive, inactive, group other
    transitions_list = sorted([(transition, transitions[transition]) for transition in transitions if transition[1] != f'Inactive ({end})'], key=lambda a : a[1], reverse=True)[:10]

    transitions_keys = [transition[0] for transition in transitions_list]

    transitions_keys.append((f'{initial_state} ({start})', f'Inactive ({end})'))

    grouped_transitions = {}

    total_travis = sum([transitions[transition] for transition in transitions if transition[0] == (f'{initial_state} ({start})')])

    total_other = sum([transitions[transition] for transition in transitions if transition not in transitions_keys])

    for transition in transitions:
        if transition not in transitions_keys:
            if (f'{initial_state} ({start}) (n={total_travis})', f'Other {end} (n={total_other})') not in grouped_transitions:
                grouped_transitions[(f'{initial_state} ({start}) (n={total_travis})', f'Other {end} (n={total_other})')] = 0

            grouped_transitions[(f'{initial_state} ({start}) (n={total_travis})', f'Other {end} (n={total_other})')] += transitions[transition]
        else:
            grouped_transitions[(f'{transition[0]} (n={total_travis})', f'{transition[1]} (n={transitions[transition]})')] = transitions[transition]
    
    return grouped_transitions    

def get_labels(transitions : dict) -> list:
    labels = []

    for transition in transitions:
        if transition[0] not in labels:
            labels.append(transition[0])
        if transition[1] not in labels:
            labels.append(transition[1])

    return labels

def get_fig_dict(transitions : dict, labels : list, colors : list) -> dict:
    fig_dict = dict(
        source = [labels.index(transition[0]) for transition in transitions],
        target = [labels.index(transition[1]) for transition in transitions],
        value = [transitions[transition] for transition in transitions],
        color = [colors[labels.index(transition[1])] for transition in transitions]
    )

    return fig_dict

def get_repos_with_more_than_one_tool(tools_by_year : dict) -> dict:
    repos_with_more_than_one_tool = {}

    for year in tools_by_year:
        repos_with_more_than_one_tool[year] = set()

        for repo in tools_by_year[year]:
            if len(tools_by_year[year][repo]) > 1:
                repos_with_more_than_one_tool[year].add(repo)

    return repos_with_more_than_one_tool

def get_repos_with_more_than_one_tool_graph(repos_with_more_then_one_tool):
    graph = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values" : [{'year' : year, 'number_of_repos' : len(repos_with_more_then_one_tool[year])} for year in repos_with_more_then_one_tool]
        },
        "layer" : [
            {
                "mark": "bar"
            },
            {
                "mark": {
                    "type": "text",
                    "align": "center",
                    "baseline": "middle",
                    "dx" : 15,
                    "angle" : 270
                }, 
                "encoding": {
                    "text": {"field": "number_of_repos", "type": "quantitative"}
                }
            }
        ],
        "encoding": {
            "x": {
                "field": "year",
                "type": "nominal",
                "title" : "Year"
            },
            "y": {
                "field": "number_of_repos",
                "type": "quantitative",
                "title" : "# of repositories"
            }
        }
    }

    return graph

print('Grouping tool histories by year')
tools_by_year = group_tool_histories_by_year(tool_histories=tool_histories, start=2012, end=2023)

print(json.dumps({year : len(tools_by_year[year].keys()) for year in tools_by_year}, indent=2))

repos_with_more_than_one_tool = get_repos_with_more_than_one_tool(tools_by_year=tools_by_year)

repos_with_more_than_one_tool_graph = get_repos_with_more_than_one_tool_graph(repos_with_more_then_one_tool=repos_with_more_than_one_tool)

with open(f'repos_with_more_than_one_tool_graph.json', 'w') as file:
     file.write(json.dumps(repos_with_more_than_one_tool_graph, indent=2))

#streaks = get_repo_activity_streaks(tool_histories_by_year=tools_by_year, start=2012, end=2023)

#streak_repo_sets = get_streak_repos(streaks=streaks, start=2012, end=2023)

# print(len(streak_repo_sets[(2012, 2023)]))

# print('Making n tools histograms')
# n_tools_histograms, percentage_n_tools_histograms = get_repos_with_n_tools_histograms(tool_histories_by_year=tools_by_year)

# for year in n_tools_histograms:
#     with open(f'number_of_tools_histograms/{year}.json', 'w') as file:
#         file.write(json.dumps(n_tools_histograms[year], indent=2))

# for year in percentage_n_tools_histograms:
#     with open(f'number_of_tools_histograms/{year}_percentages.json', 'w') as file:
#         file.write(json.dumps(percentage_n_tools_histograms[year], indent=2))

# n_tools_stacked_bar, n_tools_percentage_stacked_bar = get_repos_with_n_tools_stacked_bar(tool_histories_by_year=tools_by_year)

# with open(f'n_tools_stacked_bar_chart-{filename}.json', 'w') as file:
#     file.write(json.dumps(n_tools_stacked_bar, indent=2))

# with open(f'n_tools_percentages_stacked_bar_chart-{filename}.json', 'w') as file:
#     file.write(json.dumps(n_tools_percentage_stacked_bar, indent=2))

# print('Getting tool counts')
# tool_counts_by_year = {year : get_tool_counts(tool_histories_for_year=tools_by_year[year]) for year in tools_by_year}

# tool_count_percentages_by_year = get_tool_counts_percentages_by_year(tool_counts_by_year=tool_counts_by_year, tool_histories_by_year=tools_by_year)

# tool_counts_by_year_group_other = get_tool_counts_by_year_group_other(tool_counts_by_year=tool_counts_by_year, tool_count_percentages_by_year=tool_count_percentages_by_year)

# print('Making stacked bar chart')
# stacked_bar_chart = get_tool_counts_stacked_bar_chart(tool_counts_by_year=tool_counts_by_year_group_other)

# with open(f'tool_counts_stacked_bar_chart.json-{filename}', 'w') as file:
#     file.write(json.dumps(stacked_bar_chart, indent=2))

print('Getting tool transitions by year (2012, 2023)')
tool_transitions_by_year_2012_2023 = get_tool_transitions_by_year(tool_histories=tool_histories, ignore_first_if_no_tools=True, repo_set=streak_repo_sets[(2012, 2023)])

print('Making tool changes percentage graph (2012, 2023)')
tool_changes_percentage_graph = get_tool_changes_percentage_graph(tool_transitions_by_year=tool_transitions_by_year_2012_2023, active_repo_streak=(2012, 2023), repo_set=streak_repo_sets[(2012, 2023)])

with open(f'tool_changes_percentage_graph_2012_2023.json-{filename}', 'w') as file:
    file.write(json.dumps(tool_changes_percentage_graph, indent=2))

print('Getting tool transitions by year')
tool_transitions_by_year = get_tool_transitions_by_year(tool_histories=tool_histories, ignore_first_if_no_tools=True)

print('Making tool changes percentage graph')
tool_changes_percentage_graph = get_tool_changes_percentage_graph(tool_transitions_by_year=tool_transitions_by_year)

with open(f'tool_changes_percentage_graph.json-{filename}', 'w') as file:
    file.write(json.dumps(tool_changes_percentage_graph, indent=2))

# print('Making individual tool change by year graphs')
# github_actions_changes_by_year = get_individual_tool_change_by_year_graph(tool_transitions_by_year=tool_transitions_by_year_2012_2023, tool='GitHubActions')

# with open(f'github_actions_changes_by_year.json-{filename}', 'w') as file:
#     file.write(json.dumps(github_actions_changes_by_year, indent=2))


# repos_using_travis_ci = get_repos_using_tool(tools_for_year=tools_by_year[2019], tools='Travis')

# repos_active_in_2023 = tools_by_year[2023].keys()

# active_repos_in_2023_using_travis_ci = repos_using_travis_ci.intersection(repos_active_in_2023)

# repos_using_gha_that_used_travis = get_repos_using_tool(tools_for_year=tools_by_year[2023], tools='GitHubActions', no_tools='Travis', repo_set=active_repos_in_2023_using_travis_ci)

# repos_using_travis_that_used_travis = get_repos_using_tool(tools_for_year=tools_by_year[2023], tools='Travis', no_tools='GitHubActions', repo_set=active_repos_in_2023_using_travis_ci)

# repos_using_both = get_repos_using_tool(tools_for_year=tools_by_year[2023], tools=['Travis', 'GitHubActions'], repo_set=active_repos_in_2023_using_travis_ci)


# print(f'Repos using Travis CI: {len(active_repos_in_2023_using_travis_ci)}')
# print(f'Repos using GitHub Actions that used Travis CI: {len(repos_using_gha_that_used_travis)}')
# print(f'Repos using Travis CI that used Travis CI: {len(repos_using_travis_that_used_travis)}')
# print(f'Repos using both: {len(repos_using_both)}')

# # Percentages

# print(f'Repos using GitHub Actions that used Travis CI: {len(repos_using_gha_that_used_travis) / len(active_repos_in_2023_using_travis_ci) * 100}%')
# print(f'Repos using Travis CI that used Travis CI: {len(repos_using_travis_that_used_travis) / len(active_repos_in_2023_using_travis_ci) * 100}%')
#print(f'Repos using both: {len(repos_using_both) / len(active_repos_in_2023_using_travis_ci) * 100}%')

# repos_using_gha_2023 = get_repos_using_tool(tools_for_year=tools_by_year[2023], tools='GitHubActions')

# repos_active_2019 = set(tools_by_year[2019].keys())

# repos_using_gha_2023_not_active_2019 = repos_using_gha_2023.difference(repos_active_2019)

# print(f'Repos using GitHub Actions in 2023: {len(repos_using_gha_2023)}')
# print(f'Repos using GitHub Actions in 2023 but not active in 2019: {len(repos_using_gha_2023_not_active_2019)}')
# print(f'Repos using GitHub Actions in 2023 but not active in 2019: {len(repos_using_gha_2023_not_active_2019) / len(repos_using_gha_2023) * 100}%')

# snapshots_by_year = get_snapshots_by_year(tool_histories=tool_histories, start=2012, end=2023)

# snapshots_tool_counts_by_year = get_snapshots_tool_counts_by_year(snapshots_by_year=snapshots_by_year)

# snapshots_tool_counts_graph = get_snapshots_tool_counts_graph(snapshots_tool_counts_by_year=snapshots_tool_counts_by_year)

# with open(f'snapshots_tool_counts_graph.json-{filename}', 'w') as file:
#     file.write(json.dumps(snapshots_tool_counts_graph, indent=2))

# time_to_first_tool = get_time_to_first_tool(tool_histories=tool_histories)

# repos_created_by_year = get_repos_created_in_year()

# mean_time_to_fist_tool = get_mean_time_to_first_tool_by_year(repos_created_by_year=repos_created_by_year, time_to_first_tool=time_to_first_tool)

# mean_time_to_first_tool_graph = get_mean_time_to_first_tool_graph(mean_time_to_first_tool=mean_time_to_fist_tool)

# with open(f'mean_time_to_first_tool_graph.json-{filename}', 'w') as file:
#     file.write(json.dumps(mean_time_to_first_tool_graph, indent=2))

# repos_using_travis_ci_only_2019 = get_repos_using_tool(tools_for_year=tools_by_year[2019], tools='Travis', no_tools='EXCLUDE_ALL_OTHER_TOOLS')

# repos_active_in_2023 = tools_by_year[2023].keys()

# repos_using_travis_ci_only_2019_active_in_2023 = repos_using_travis_ci_only_2019.intersection(repos_active_in_2023)

# repos_using_travis_ci_only_2019_active_2023_toolsets = {repo : '+'.join(sorted(tools_by_year[2023][repo])) for repo in repos_using_travis_ci_only_2019_active_in_2023}

# repos_using_travis_ci_only_2019_active_2023_toolset_counts = {}

# for repo in repos_using_travis_ci_only_2019_active_2023_toolsets:
#     toolset = repos_using_travis_ci_only_2019_active_2023_toolsets[repo]

#     if toolset not in repos_using_travis_ci_only_2019_active_2023_toolset_counts:
#         repos_using_travis_ci_only_2019_active_2023_toolset_counts[toolset] = 0

#     repos_using_travis_ci_only_2019_active_2023_toolset_counts[toolset] += 1

# repos_using_travis_ci_only_2019_active_2023_toolsets_sorted_most_popular = sorted(repos_using_travis_ci_only_2019_active_2023_toolset_counts.items(), key=lambda item : item[1], reverse=True)

# transitions = get_transitions(initial_state='Travis', initial_set=repos_using_travis_ci_only_2019, final_state=repos_using_travis_ci_only_2019_active_2023_toolsets, start=2019, end=2023)

# labels = get_labels(transitions=transitions)

# node = dict(
#     pad = 15,
#     thickness = 20,
#     line = dict(color = "black", width = 0.5),
#     label = labels,
#     color = colors,
# )

# fig_dict = get_fig_dict(transitions=transitions, labels=labels, colors=colors)

# fig = go.Figure(data=[go.Sankey(
#     node = node,
#     link = fig_dict
# )])

# fig.show()

#fig.write_image(f'travis_ci_only_2019_active_2023_sankey.png')