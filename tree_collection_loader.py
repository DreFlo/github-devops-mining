from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from functools import reduce
import random
import threading
import signal
import argparse
import bson

from github_api_wrappers import *
from mongodb_wrappers import *
from colorama import Fore, Style
from tools import *


# Command line arguments
parser = argparse.ArgumentParser(description='Load trees from GitHub repositories into MongoDB')

parser.add_argument('--delete-tools', action='store_true', help='Delete all tools from the repo histories collection and exit')
parser.add_argument('--check-database', action='store_true', help='Check the database for inconsistencies with check file and exit')
parser.add_argument('--delete-check-file', action='store_true', help='Delete the repository check file')
parser.add_argument('--test-github-api-limits', action='store_true', help='Test the GitHub API limits and exit')
parser.add_argument('--interrupt-at', type=str, default=None, help='Interrupt the program at the specified time, format: YYYY-MM-DDTHH:MM')
parser.add_argument('--sanity-check', action='store_true', help='Perform a sanity check on the database and exit')

interrupt_number = 0
interrupted = threading.Event()

check_file_lock = threading.Lock()

parsed_repositories = {}

def initialize_parsed_repositories():
    if os.path.exists('repository_check_file'):
        with open('repository_check_file', 'r') as check_file:
            for line in check_file:
                check = json.loads(line)
                parsed_repositories[check['repo_full_name']] = {'trees' : check['trees'], 'time' : check['time']}

def split_tree_into_subtrees(tree : dict) -> list:
        # Initialize subtrees with the root tree
        subtrees = {'' : {'date' : tree['date'], 'repo_full_name' : tree['repo_full_name'], 'tree' : [], 'sha' : tree['sha'], 'path' : ''}}

        # Add subtrees to the subtrees dictionary
        for subtree in tree['tree']:
            if subtree['type'] == 'tree':
                subtrees[subtree['path']] = {'date' : tree['date'], 'repo_full_name' : tree['repo_full_name'], 'tree' : [], 'sha' : subtree['sha'], 'path' : subtree['path']}

        # Add nodes to the subtrees
        for node in tree['tree']:
            subtree_path = '/'.join(node['path'].split('/')[:-1])

            if subtree_path in subtrees:
                subtrees[subtree_path]['tree'].append(node)


        # Split subtrees that are too big
        size_limited_subtrees = []

        for subtree in subtrees.values():
            encoded_size = sys.getsizeof(bson.BSON.encode(subtree))
            if encoded_size >= 16793600:
                print(Fore.BLUE + threading.current_thread().name + ':\t' + Fore.YELLOW + f'Splitting subtree with {len(subtree["tree"])} nodes' + Style.RESET_ALL)
                parts = int(encoded_size / 16793600) + 1
                parted_subtrees = []
                while True:
                    # Attempt to split the subtree into parts
                    for i in range(parts):
                        parted_subtree = {key : value for key, value in subtree.items() if key != 'tree'}
                        parted_subtree['tree'] = subtree['tree'][i * len(subtree['tree']) // parts : (i + 1) * len(subtree['tree']) // parts]
                        parted_subtree['part'] = i
                        parted_subtrees.append(parted_subtree)

                    too_large = False

                    # Check if the parts are small enough
                    for parted_subtree in parted_subtrees:
                        # If the parts are not small enough, try again with more parts
                        if sys.getsizeof(bson.BSON.encode(parted_subtree)) >= 16793600:
                            too_large = True
                            break

                    if too_large:
                        parts += 1
                        parted_subtrees = []
                        continue
                    break
                size_limited_subtrees.extend(parted_subtrees)
                print(Fore.BLUE + threading.current_thread().name + ':\t' + Fore.YELLOW + f'Split subtree into {parts} parts ({sum([len(parted_subtree["tree"] for parted_subtree in parted_subtrees)])} nodes)' + Style.RESET_ALL)
            else:
                size_limited_subtrees.append(subtree)

        return size_limited_subtrees

def find_tools_and_store_in_database(trees_to_process) -> bool:
    global interrupted
    wrapper = MongoDBWrapper()
    repo_tools = {'repo_full_name' : trees_to_process['full_name']}
    
    # start = time.time()

    # Detect tools
    repo_tools['snapshots'] = find_repo_trees_tools(trees_to_process['full_name'], trees_to_process['default_branch'],trees_to_process['trees'])

    # end = time.time()

    #print(Fore.BLUE + threading.current_thread().name + ':\t' + Style.RESET_ALL + f'Time taken to detect tools in {len(trees_to_process["trees"])} trees: {end - start}')

    tries = 0

    # Add tools to database
    while tries < 5:
        try:
            if not wrapper.has_been_processed(repo_tools['repo_full_name']):
                wrapper.add_repo_tools(repo_tools)
            break
        except Exception as e:
            print(e)
            print(Fore.BLUE + threading.current_thread().name + '\t' + Fore.RED + 'Retrying to add tools' + Style.RESET_ALL)
            tries += 1
            continue

    if tries == 5:
        print(Fore.BLUE + threading.current_thread().name + ':\t' + Fore.RED + 'Failed to add tools' + Style.RESET_ALL)
        return False
    else:
        #print(Fore.BLUE + 'PROCESSER THREAD:\t' + Fore.GREEN + 'Tools added successfully' + Style.RESET_ALL)
        return True

def get_repository_trees(repository : dict) -> None:
    global interrupted, parsed_repositories, check_file_lock
    wrapper = MongoDBWrapper()

    if interrupted.is_set():
        print(Fore.MAGENTA + threading.current_thread().name + ':\t' + Fore.GREEN + 'Interrupted, exiting safely' + Style.RESET_ALL)
        return

    if repository['full_name'] in parsed_repositories:
        print(Fore.MAGENTA + threading.current_thread().name + ':\t' + Fore.YELLOW + f'Skipping repository {repository["full_name"]}, already parsed' + Style.RESET_ALL)
        return

    # Check if has already been processed
    if wrapper.has_been_processed(repository['full_name']):
        print(Fore.MAGENTA + threading.current_thread().name + ':\t' + Fore.YELLOW + f'Skipping repository {repository["full_name"]}, already processed' + Style.RESET_ALL)
        return
    
    repo_full_name = repository['full_name']

    print(Fore.MAGENTA + threading.current_thread().name + ':\t' + Style.RESET_ALL + f'Processing repository: {repo_full_name}')

    start = time.time()

    commit_count, first_commit = get_commit_count_and_first_commit(repo_full_name)

    print(Fore.MAGENTA + threading.current_thread().name + ':\t' + Style.RESET_ALL + f'Commit count: {commit_count}')

    if commit_count == 0 or first_commit == None:
        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Fore.YELLOW + f'Skipping repository {repo_full_name}, could not get first commit or commit_count' + Style.RESET_ALL)
        return

    repo_snapshot_commits = get_snapshot_commits_optimized(
        repo_full_name, 
        commit_count,
        first_commit,
        dateutil.parser.parse(repository['updated_at']), 
        timedelta(days=90))

    if repo_snapshot_commits is None:
        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Fore.YELLOW + f'Skipping repository {repo_full_name}, could not get first commit' + Style.RESET_ALL)
        return

    repo_snapshot_trees = get_repo_trees(full_name=repo_full_name, commits=repo_snapshot_commits)

    for i in range(len(repo_snapshot_commits)):
        repo_snapshot_trees[i]['date'] = dateutil.parser.isoparse(repo_snapshot_commits[i]['commit']['author']['date'])
        repo_snapshot_trees[i]['sha'] = repo_snapshot_commits[i]['sha']
        repo_snapshot_trees[i]['repo_full_name'] = repo_full_name
        if 'url' in repo_snapshot_trees[i]:
            del repo_snapshot_trees[i]['url']

    if len(repo_snapshot_trees) == 0:
        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Style.RESET_ALL + f'No trees found for {repo_full_name}')
        return

    stored_trees = find_tools_and_store_in_database({'full_name' : repo_full_name, 'default_branch' : repository['default_branch'], 'trees' : repo_snapshot_trees})

    stop = time.time()

    if (stored_trees):
        check_file_lock.acquire()

        parsed_repositories[repo_full_name] = {'trees' : len(repo_snapshot_trees), 'time' : stop - start}

        check_file_lock.release()
    else:
        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Fore.RED + f'Failed to store trees for {repo_full_name}' + Style.RESET_ALL)



def set_interrupted_flag(_signal, _frame) -> None:
    global interrupted, interrupt_number
    interrupt_number += 1
    if interrupt_number == 1:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.YELLOW + f'Interrupted once (time: {datetime.now()}), stopping after current repository' + Style.RESET_ALL)
        interrupted.set()
    elif interrupt_number == 2:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + f'Interrupted again time: {datetime.now()}), stopping immediately' + Style.RESET_ALL)
        sys.exit(0)

def check_database() -> None:
    wrapper = MongoDBWrapper()
    error = False
    with open('repository_check_file', 'r') as check_file:
        for line in check_file:
            check = json.loads(line)
            repo_full_name = check['repo_full_name']
            tree_count = check['trees']
            repo_history_count = wrapper.count_repo_snapshots(repo_full_name)
            if tree_count != repo_history_count:
                error = True
                print(f'{repo_full_name} has {tree_count} trees in the check file and {repo_history_count} trees in the database')
    if not error:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.GREEN + 'Database check completed successfully' + Style.RESET_ALL)
    else:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + 'Database check failed' + Style.RESET_ALL)

def sanity_check() -> None:
    wrapper = MongoDBWrapper()
    with open('repository_check_file', 'r') as check_file:
        for line in check_file:
            check = json.loads(line)
            repo_full_name = check['repo_full_name']
            tree_count = check['trees']
            repo = wrapper.get_repositories(filter={"full_name": repo_full_name}, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0})[0]
            trimester_count = dateutil.parser.parse(repo['updated_at']).year * 4 + (dateutil.parser.parse(repo['updated_at']).month - 1) // 3 - dateutil.parser.parse(repo['created_at']).year * 4 - (dateutil.parser.parse(repo['created_at']).month - 1) // 3 + 1
            # Check if same vicinity
            if tree_count / trimester_count > 1.5 or trimester_count / tree_count > 1.5:
                print(f'{repo_full_name} has {tree_count} trees and {trimester_count} trimesters')

def test_github_api_limits(repositories : Cursor) -> None:
    repositories_list = list(repositories)
    its = 0
    while True:
        for repository in repositories_list:
            get_repo(repository['full_name'])
            its += 1
            if its % 100 == 0:
                print(f'Performed {its} requests')

interrupt_at = None

def raise_sigint() -> None:
    signal.raise_signal(signal.SIGINT)

def save_check_file() -> None:
    global parsed_repositories, check_file_lock
    with open('repository_check_file', 'w') as check_file:
        check_file_lock.acquire()
        for repo_full_name, repo_info in parsed_repositories.items():
            check_file.write(json.dumps({'repo_full_name' : repo_full_name, 'trees' : repo_info['trees'], 'time' : repo_info['time']}) + '\n')
        check_file_lock.release()

def save_check_file_every_15_seconds() -> None:
    while True:
        save_check_file()
        if interrupted.is_set():
            break
        time.sleep(15)
    return

def main():
    global interrupt_at
    wrapper = MongoDBWrapper()

    if parser.parse_args().interrupt_at is not None:
        interrupt_at = datetime.strptime(parser.parse_args().interrupt_at, '%Y-%m-%dT%H:%M')
        alarm_time = (interrupt_at - datetime.now()).total_seconds()
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.YELLOW + f'Interrupting at {interrupt_at}' + Style.RESET_ALL)
        timer = threading.Timer(alarm_time, raise_sigint)
        timer.daemon = True
        timer.start()
        
    if parser.parse_args().delete_tools:
        print(Fore.LIGHTCYAN_EX + threading.current_thread().name + ':\t' + Fore.RED + 'Deleting all tools from the repo histories collection' + Style.RESET_ALL)
        print("To delete all tools from the repo histories collection, type 'DELETE' and press enter")
        if input() == 'DELETE':
            wrapper.delete_repo_histories()
        return
    
    if parser.parse_args().check_database:
        print(Fore.LIGHTCYAN_EX + threading.current_thread().name + ':\t' + Fore.YELLOW + 'Checking database' + Style.RESET_ALL)
        check_database()
        return
    
    if parser.parse_args().sanity_check:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.YELLOW + 'Performing sanity check' + Style.RESET_ALL)
        sanity_check()
        return
    
    if parser.parse_args().test_github_api_limits:
        print(Fore.LIGHTCYAN_EX + threading.current_thread().name + ':\t' + Fore.YELLOW + 'Testing GitHub API limits' + Style.RESET_ALL)
        filter = {}
        test_github_api_limits(wrapper.get_repositories(filter=filter, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0}))
        return
    
    if parser.parse_args().delete_check_file:
        print(Fore.LIGHTCYAN_EX + threading.current_thread().name + ':\t' + Fore.RED + 'Deleting repository check file' + Style.RESET_ALL)
        print(Fore.LIGHTCYAN_EX + threading.current_thread().name + ':\t' + "To delete the check file, type 'DELETE' and press enter")
        if input() == 'DELETE':
            if os.path.exists('repository_check_file'):
                os.remove('repository_check_file')

    initialize_parsed_repositories()

    signal.signal(signal.SIGINT, set_interrupted_flag)

    saver_thread = threading.Thread(target=save_check_file_every_15_seconds, daemon=False)

    saver_thread.start()

    while not interrupted.is_set():
        futures = []
        repositories = wrapper.get_random_processed_repositories(1000)

        with ThreadPoolExecutor(max_workers=32) as executor:
            for repository in repositories:
                f = executor.submit(get_repository_trees, repository)
                futures.append(f)

        not_done = futures
        while not_done:
            _, not_done = wait(not_done, timeout=1, return_when=FIRST_COMPLETED)
            
    saver_thread.join()

    sys.exit(0)

if __name__ == '__main__':
    main()