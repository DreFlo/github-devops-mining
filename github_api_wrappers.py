from datetime import datetime, timedelta
import sys
import time
import dateutil.parser
import requests
import json
import os
import base64

from dotenv import load_dotenv

from requests.structures import CaseInsensitiveDict
from urllib.parse import parse_qs, urlparse
from colorama import Fore, Style


# Load Github Token
load_dotenv()

TOKEN = os.getenv('GITHUB_TOKEN')

REQUEST_COUNT = 0
CONNECTION_ERROR_COUNT = 0

RATE_LIMIT_RESET_TIME = None

def send_get_request_wait_for_rate_limit(**kwargs) -> requests.Response:
    global REQUEST_COUNT, RATE_LIMIT_RESET_TIME, CONNECTION_ERROR_COUNT
    REQUEST_COUNT += 1

    # print(f'[{REQUEST_COUNT}] {kwargs}')

    if RATE_LIMIT_RESET_TIME:
        if datetime.now() < RATE_LIMIT_RESET_TIME:
            print( Fore.YELLOW + f'Rate limit reached, waiting until reset at {RATE_LIMIT_RESET_TIME}' + Style.RESET_ALL)
            time.sleep((RATE_LIMIT_RESET_TIME - datetime.now()).total_seconds())
            RATE_LIMIT_RESET_TIME = None
            print(Fore.GREEN + 'Rate limit reset, continuing' + Style.RESET_ALL)

    kwargs['timeout'] = None
    
    while True:
        try:
            response = requests.get(**kwargs)
            break
        except requests.exceptions.ConnectionError:
            print(Fore.RED + 'Connection error, waiting 2 seconds' + Style.RESET_ALL)
            REQUEST_COUNT += 1
            CONNECTION_ERROR_COUNT += 1
            time.sleep(2)
            continue
    
    if response.headers['X-RateLimit-Remaining'] == '0':
        RATE_LIMIT_RESET_TIME = datetime.fromtimestamp(float(response.headers['X-RateLimit-Reset']))

    return response

def reset_request_count() -> None:
    global REQUEST_COUNT
    REQUEST_COUNT = 0

# Get repo names for query string
def get_repository_full_names(query : str = 'path:.github/workflows extension:yaml', per_page : int = 5) -> list:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'

    # Query Parameters
    params = CaseInsensitiveDict()
    params['q'] = query
    params['per_page'] = per_page
    params['page'] = 1

    url = 'https://api.github.com/search/code'

    response = send_get_request_wait_for_rate_limit(url= url, params=params, headers=headers)

    items = response.json()['items']

    return [item['repository']['full_name'] for item in items]

# Get repo information
def get_repo(full_name : str) -> json:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'

    url = f'https://api.github.com/repos/{full_name}'

    response = send_get_request_wait_for_rate_limit(url=url, headers=headers)

    return response.json()

# Get commits on default branch
def get_repo_commits(full_name : str, per_page : str = 100, max_pages : str = sys.maxsize, since : str = None, until : str = None) -> list:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'

    url = f'https://api.github.com/repos/{full_name}/commits'

    # Query Parameters
    params = CaseInsensitiveDict()
    params['per_page'] = per_page
    params['page'] = 1
    if since:
        params['since'] = since
    if until:
        params['until'] = until

    commits = []

    # Go through pages to get all commits
    while params['page'] <= max_pages:
        response = send_get_request_wait_for_rate_limit(url=url, params=params, headers=headers)
        commits = commits + response.json()
        params['page'] += 1
        # If number of commits retrieved is lesser than page limit, the current page is the last one
        if len(response.json()) < 100:
            break

    return commits

# Downloads repo contents to a zip
def download_repo_snapshot(full_name : str, ref : str, path : str = '') -> None:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github.raw'
    headers['Authorization'] = f'Bearer {TOKEN}'

    url = f'https://api.github.com/repos/{full_name}/zipball/{path}'

    # Query Parameters
    params = CaseInsensitiveDict()
    params['ref'] = ref

    response = send_get_request_wait_for_rate_limit(url=url, params=params, headers=headers, allow_redirects=True)

    with open(f'{full_name.split("/")[1]}-{ref[:6]}.zip', 'wb') as repo_contents:
        repo_contents.write(response.content)

    return None

def get_repo_tree(full_name : str, tree_sha : str, recursive : bool = True) -> list:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'

    url = f'https://api.github.com/repos/{full_name}/git/trees/{tree_sha}'

    # Query Parameters
    params = CaseInsensitiveDict()
    if recursive:
        params['recursive'] = 'true'

    response = send_get_request_wait_for_rate_limit(url=url, params=params, headers=headers)

    return response.json()

def get_commit_comparison(full_name : str, commit_1_sha : str, commit_2_sha) -> json:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    #headers['Accept'] = 'application/vnd.github.diff' # If you want the response to come with diff
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'

    url = f'https://api.github.com/repos/{full_name}/compare/{commit_1_sha}...{commit_2_sha}'

    response = send_get_request_wait_for_rate_limit(url=url, headers=headers)

    return response.json()

# Get timestamp from commit in datetime object
def get_commit_timestamp(commit : dict) -> datetime:
    return dateutil.parser.isoparse(commit['commit']['author']['date'])

# Get commits separated by roughly timedelta
def get_repo_snapshots(commits : list, commit_interval : timedelta) -> list:
    commits.sort(key=get_commit_timestamp)

    repo_snapshots = []

    for i in range(len(commits)):
        if i == 0 or i == len(commits) - 1:
            repo_snapshots.append(commits[i])
        elif get_commit_timestamp(commits[i]) - get_commit_timestamp(repo_snapshots[-1]) >= commit_interval:
            repo_snapshots.append(commits[i])

    return repo_snapshots

def get_snapshot_commits_retrieve_all_commits(full_name : str, commit_interval : timedelta = timedelta(days=90)) -> list:
    commits = get_repo_commits(full_name=full_name)
    return get_repo_snapshots(commits=commits, commit_interval=commit_interval)

def get_snapshot_commits_query_timedelta(full_name : str, created_at : datetime, updated_at : datetime, commit_count : int, commit_interval : timedelta = timedelta(days=90)) -> list:
    # Get first commit
    result = [get_first_commit(full_name)]

    commits = []

    # Get commits in intervals
    day_window = timedelta(days=7)
    extended_search_tries = 0

    prev_until = None
    ignore_day_window = False

    while get_commit_timestamp(result[-1]) + commit_interval < updated_at:
        if extended_search_tries > 100:
            print(f'Extended search tries exceeded for {full_name}')
            break
        elif day_window > commit_interval:
            ignore_day_window = True
            extended_search_tries += 1
            since = (prev_until if prev_until is not None else (get_commit_timestamp(result[-1]) + commit_interval)).isoformat()
            until = (prev_until + commit_interval * 8 if prev_until is not None else (get_commit_timestamp(result[-1]) + commit_interval * 8)).isoformat()
            prev_until = dateutil.parser.isoparse(until)         
        else:
            since = (get_commit_timestamp(result[-1]) + commit_interval - day_window).isoformat()
            until = (get_commit_timestamp(result[-1]) + commit_interval + day_window).isoformat()

        commits = get_repo_commits(full_name=full_name, since=since, until=until, max_pages=1)

        # If no commits are retrieved, increase the day window and try again
        if len(commits) == 0:
            if not ignore_day_window:
                day_window_days = day_window.days
                day_window = timedelta(days=day_window_days*2)
            continue

        commits.sort(key=get_commit_timestamp)

        if result[-1]['sha'] == commits[-1]['sha']:
            if not ignore_day_window:
                day_window_days = day_window.days
                day_window = timedelta(days=day_window_days*2)
            continue

        result.append(commits[-1])

        extended_search_tries = 0
        ignore_day_window = False
        day_window = timedelta(days=3)

    # Get last commit
    commits = get_repo_commits(full_name=full_name, per_page=1, max_pages=1)

    if result[-1]['sha'] != commits[0]['sha']:
        result.append(commits[0])

    return result

def get_snapshot_commits_optimized(full_name : str, commit_count : int, created_at : datetime, updated_at : datetime, commit_interval : timedelta = timedelta(days=90)) -> list:
    commit_density = commit_count / (updated_at - created_at).days # commits per day

    commit_interval_days = commit_interval.days

    commits_per_interval = commit_interval_days * commit_density

    # If, on average, there are less than 200 commits per interval, use the retrieve all commits method
    # This is to optimize the number of requests made
    if commits_per_interval <= 200: # Github API limit is 100 commits per page, number is double to account for sparse commits since it is an average
        return get_snapshot_commits_retrieve_all_commits(full_name=full_name, commit_interval=commit_interval)
    else:
        return get_snapshot_commits_query_timedelta(full_name=full_name, created_at=created_at, updated_at=updated_at, commit_count=commit_count, commit_interval=commit_interval)


def get_repo_contents(full_name : str, path : str = '', sha : str = None) -> list:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'

    params = CaseInsensitiveDict()
    if sha:
        params['sha'] = sha


    url = f'https://api.github.com/repos/{full_name}/contents/{path}'

    response = send_get_request_wait_for_rate_limit(url=url, headers=headers, params=params)

    return response.json()

def get_repo_trees(full_name : str, commits : list) -> list:
    return [get_repo_tree(full_name=full_name, tree_sha=commit['sha'], recursive=True) for commit in commits]

def get_api_rate_limits() -> json:
    # Standard Request Header
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'

    url = 'https://api.github.com/rate_limit'

    response = send_get_request_wait_for_rate_limit(url=url, headers=headers)

    return response.json()

# Function adapted from https://brianli.com/2022/07/python-get-number-of-commits-github-repository/
def get_commits_count(repo_full_name : str) -> int:
    """
    Returns the number of commits to a GitHub repository.
    """
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'
    url = f"https://api.github.com/repos/{repo_full_name}/commits?per_page=1"
    r = send_get_request_wait_for_rate_limit(headers=headers, url=url)
    links = r.links
    rel_last_link_url = urlparse(links["last"]["url"])
    rel_last_link_url_args = parse_qs(rel_last_link_url.query)
    rel_last_link_url_page_arg = rel_last_link_url_args["page"][0]
    commits_count = int(rel_last_link_url_page_arg)
    return commits_count

def get_first_commit(repo_full_name : str) -> json:
    headers = CaseInsensitiveDict()
    headers['Accept'] = 'application/vnd.github+json'
    headers['Authorization'] = f'Bearer {TOKEN}'
    url = f"https://api.github.com/repos/{repo_full_name}/commits?per_page=1"
    r = send_get_request_wait_for_rate_limit(headers=headers, url=url)
    links = r.links
    rel_last_link_url = links["last"]["url"]
    r = send_get_request_wait_for_rate_limit(headers=headers, url=rel_last_link_url)
    return r.json()[0]


# Hugo
def decoded_base_64(fileloc):
    result = send_get_request_wait_for_rate_limit(url=fileloc, headers={'Authorization' : f'Bearer {TOKEN}'})
    data = json.loads(result.content)

    decoded_content = base64.b64decode(data["content"])

    return f"{decoded_content}"
