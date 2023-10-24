import os
import json

dir = "check_files"

parsed_repositories = {}

for filename in os.listdir(dir):
    f = os.path.join(dir, filename)
    if os.path.isfile(f):
        with open(f, 'r') as check_file:
            for line in check_file:
                check = json.loads(line)
                parsed_repositories[check['repo_full_name']] = {'trees' : check['trees'], 'time' : float(check['time'])}

avg_time = sum(repo['time'] for repo in parsed_repositories.values()) / len(parsed_repositories)

total_time = avg_time * 200447

total_time_hours = total_time / 3600

total_time_hours_parallel = total_time_hours / (5 * 16)

print('avg time per repo (s):', avg_time)
print('total hours (5 proc * 16 threads)', total_time_hours_parallel)