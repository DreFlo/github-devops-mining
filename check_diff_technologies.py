import json
from colorama import Fore, Style
from enum import Enum
import random

import numpy as np

class DevOpsTechnologies(Enum):
    GITHUB_ACTIONS = 0
    JENKINS = 1
    TRAVIS_CI = 2
    CIRCLE_CI = 3
    GRADLE = 4
    RAKE = 5
    RANCHER = 6
    DOCKER = 7
    PROGRESS_CHEFF = 8
    PUPPET = 9
    NAGIOS = 10
    PROMETHEUS = 11    

# Open the file in read mode
with open('graphs\Repositories.dedup_clean_histories.json', 'r') as f:
    # Load the JSON data from the file into a dictionary
    repo_infos = json.load(f)

# Randomly sample 10000 repositories
repo_infos = random.sample(repo_infos, 10000)
print(len(repo_infos))

# Calculate number of DevOps tech stack changes: sample rate 3 months, 6 months, 1 year
_3_month_tech_stack_changes = 0
_6_month_tech_stack_changes = 0
_1_year_tech_stack_changes = 0
_3_month_tech_stack_changes_excluding_neutral_or_growth_over_6_months = 0
_3_month_tech_stack_changes_excluding_neutral_or_growth_over_1_year = 0


for repo_info in repo_infos:
    if len(repo_info['snapshots']) < 5:
        continue

    for i in range(len(repo_info['snapshots']) - 1):
        if repo_info['snapshots'][i]['tools'] != repo_info['snapshots'][i+1]['tools']:
            _3_month_tech_stack_changes += 1

    for i in range(0, len(repo_info['snapshots']) - 2, 2):
        if repo_info['snapshots'][i]['tools'] != repo_info['snapshots'][i+2]['tools']:
            _6_month_tech_stack_changes += 1

    for i in range(0, len(repo_info['snapshots']) - 4, 4):
        if repo_info['snapshots'][i]['tools'] != repo_info['snapshots'][i+4]['tools']:
            _1_year_tech_stack_changes += 1

    # # Count stack changes 3 months sample rate (don't count neutral, growth transitions as one over 6 months)
    # i = 0
    # commit_no = len(repo_info['snapshots'])
    # while i < len(repo_info['snapshots']):
    #     if i + 1 < commit_no and i + 2 < commit_no and \
    #         repo_info['snapshots'][i]['tools'] == repo_info['snapshots'][i+2]['tools']:
    #         i += 2
    #     elif i + 1 < commit_no and i + 2 < commit_no and set(repo_info['snapshots'][i]['tools']) \
    #         | set(repo_info['snapshots'][i+2]['tools']) == set(repo_info['snapshots'][i+2]['tools']):
    #         _3_month_tech_stack_changes_excluding_neutral_or_growth_over_6_months += 1
    #         i += 2
    #     elif i + 1 < commit_no and repo_info['snapshots'][i]['tools'] != repo_info['snapshots'][i+1]['tools']:
    #         _3_month_tech_stack_changes_excluding_neutral_or_growth_over_6_months += 1
    #         i += 1
    #     else:
    #         i += 1

    # # Count stack changes 3 months sample rate (don't count neutral, growth transitions as one over 1 year)
    # i = 0
    # commit_no = len(repo_info['snapshots'])
    # while i < len(repo_info['snapshots']):
    #     if i + 1 < commit_no and i + 4 < commit_no and \
    #         repo_info['snapshots'][i]['tools'] == repo_info['snapshots'][i+4]['tools']:
    #         i += 4
    #     elif i + 1 < commit_no and i + 4 < commit_no and set(repo_info['snapshots'][i]['tools']) \
    #         | set(repo_info['snapshots'][i+4]['tools']) == set(repo_info['snapshots'][i+4]['tools']):
    #         _3_month_tech_stack_changes_excluding_neutral_or_growth_over_1_year += 1
    #         i += 4
    #     elif i + 1 < commit_no and repo_info['snapshots'][i]['tools'] != repo_info['snapshots'][i+1]['tools']:
    #         _3_month_tech_stack_changes_excluding_neutral_or_growth_over_1_year += 1
    #         i += 1
    #     else:
    #         i += 1


print('Number of DevOps tech stack changes:')
print(f'3 months sample rate number of tech stack changes: {_3_month_tech_stack_changes}')
print(f'6 months sample rate number of tech stack changes: {_6_month_tech_stack_changes}')
print(f'1 year sample rate number of tech stack changes: {_1_year_tech_stack_changes}')
# print(f'3 months sample rate number of tech stack changes excluding neutral over 6 months and growth as 1: {_3_month_tech_stack_changes_excluding_neutral_or_growth_over_6_months}')
# print(f'3 months sample rate number of tech stack changes excluding neutral over 1 year and growth as 1: {_3_month_tech_stack_changes_excluding_neutral_or_growth_over_1_year}')

# Calculate number of DevOps tech stack changes: sample rate 3 months, 6 months, 1 year

# Calculate mean standard deviation of sameness factors: sample rate 3 months, 6 months, 1 year
_3_month_means = []
_6_month_means = []
_1_year_means = []

_3_month_standard_deviations = []
_6_month_standard_deviations = []
_1_year_standard_deviations = []


def sameness_factor(commit_1_technologies, commit_2_technologies):
    if len(commit_1_technologies | commit_2_technologies) == 0:
        return 0
    return len(commit_1_technologies & commit_2_technologies) / len(commit_1_technologies | commit_2_technologies)

for repo_info in repo_infos:
    if len(repo_info['snapshots']) < 5:
        continue

    sameness_factors_3_months = []

    # Calculate sameness factor between commits
    for i in range(len(repo_info['snapshots']) - 1):
        sameness_factors_3_months.append(sameness_factor(set(repo_info['snapshots'][i]['tools']), set(repo_info['snapshots'][i+1]['tools'])))

    _3_month_means.append(np.mean(sameness_factors_3_months))
    _3_month_standard_deviations.append(np.std(sameness_factors_3_months))

    sameness_factors_6_months = []

    # Calculate sameness factor between commits
    for i in range(0, len(repo_info['snapshots']) - 2, 2):
        sameness_factors_6_months.append(sameness_factor(set(repo_info['snapshots'][i]['tools']), set(repo_info['snapshots'][i+2]['tools'])))

    _6_month_means.append(np.mean(sameness_factors_6_months))
    _6_month_standard_deviations.append(np.std(sameness_factors_6_months))

    sameness_factors_1_year = []

    # Calculate sameness factor between commits
    for i in range(0, len(repo_info['snapshots']) - 4, 4):
        sameness_factors_1_year.append(sameness_factor(set(repo_info['snapshots'][i]['tools']), set(repo_info['snapshots'][i+4]['tools'])))

    _1_year_means.append(np.mean(sameness_factors_1_year))
    _1_year_standard_deviations.append(np.std(sameness_factors_1_year))

# print('\n\n')
# print('Mean and mean standard deviation of sameness factors:')
# print(f'3 months sample rate mean of sameness factors: {np.mean(_3_month_means)}')
# print(f'3 months sample rate mean standard deviation of sameness factors: {np.mean(_3_month_standard_deviations)}')
# print('\n')
# print(f'6 months sample rate mean of sameness factors: {np.mean(_6_month_means)}')
# print(f'6 months sample rate mean standard deviation of sameness factors: {np.mean(_6_month_standard_deviations)}')
# print('\n')
# print(f'1 year sample rate mean of sameness factors: {np.mean(_1_year_means)}')
# print(f'1 year sample mean standard deviation of sameness factors: {np.mean(_1_year_standard_deviations)}')

# percentage drop of stack changesfrom 3 months to 6 months
percentage_drop_3_to_6_months = (_3_month_tech_stack_changes - _6_month_tech_stack_changes) / _3_month_tech_stack_changes
print(f'Percentage drop of tech stack changes from 3 months to 6 months: {percentage_drop_3_to_6_months}')

# percentage drop of stack changesfrom 6 months to 1 year
percentage_drop_6_to_1_year = (_6_month_tech_stack_changes - _1_year_tech_stack_changes) / _6_month_tech_stack_changes
print(f'Percentage drop of tech stack changes from 6 months to 1 year: {percentage_drop_6_to_1_year}')

