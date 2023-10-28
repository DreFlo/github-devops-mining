from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from functools import reduce
import multiprocessing
import multiprocessing.connection
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

# parser.add_argument('its', nargs=1, type=int, default='', help='Number of its to perform')

interrupt_number = 0
interrupted = threading.Event()
all_threads_done = threading.Event()
saver_thread_killed = threading.Event()

check_file_lock = threading.Lock()

parsed_repositories = {}

futures = []

CHECK_FILE_PATH = ''

saver_thread = None

def initialize_parsed_repositories():
    if os.path.exists(CHECK_FILE_PATH):
        with open(CHECK_FILE_PATH, 'r') as check_file:
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
                thread_print(Fore.YELLOW + f'Splitting subtree with {len(subtree["tree"])} nodes')
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
                thread_print(Fore.YELLOW + f'Split subtree into {parts} parts ({sum([len(parted_subtree["tree"] for parted_subtree in parted_subtrees)])} nodes)')
            else:
                size_limited_subtrees.append(subtree)

        return size_limited_subtrees

def find_tools_and_store_in_database(trees_to_process, wrapper : MongoDBWrapper) -> bool:
    global interrupted
    repo_tools = {'repo_full_name' : trees_to_process['full_name']}
    
    # start = time.time()

    # Detect tools
    repo_tools['snapshots'] = find_repo_trees_tools(trees_to_process['full_name'], trees_to_process['default_branch'],trees_to_process['trees'])

    # end = time.time()

    #print(Fore.BLUE + threading.current_thread().name + ':\t' + Style.RESET_ALL + f'Time taken to detect tools in {len(trees_to_process["trees"])} trees: {end - start}')

    tries = 0

    # thread_print(f'Adding tools to database')

    # Add tools to database
    while tries < 5:
        try:
            if not wrapper.has_been_processed(repo_tools['repo_full_name']):
                wrapper.add_repo_tools(repo_tools)
            break
        except Exception as e:
            thread_print(e)
            thread_print(Fore.RED + 'Retrying to add tools')
            tries += 1
            continue

    if tries == 5:
        thread_print(Fore.RED + f'Failed to add tools ({datetime.now()})' + Style.RESET_ALL)
        return False
    else:
        thread_print(Fore.GREEN + f'Tools added successfully ({datetime.now()})' + Style.RESET_ALL)
        return True

def get_repository_trees(repository : dict, wrapper : MongoDBWrapper) -> None:
    global interrupted, parsed_repositories, check_file_lock

    if interrupted.is_set():
        return

    if repository['full_name'] in parsed_repositories:
        thread_print(Fore.YELLOW + f'Skipping repository {repository["full_name"]}, already parsed')
        return

    # Check if has already been processed
    if wrapper.has_been_processed(repository['full_name']):
        thread_print(Fore.YELLOW + f'Skipping repository {repository["full_name"]}, already processed')
        return
    
    repo_full_name = repository['full_name']

    thread_print(f'Processing repository: {repo_full_name}')

    start = time.time()

    commit_count, first_commit = get_commit_count_and_first_commit(repo_full_name=repo_full_name)#get_commits_count(repository['full_name']), get_first_commit(repository['full_name'])

    thread_print(f'Commit count: {commit_count}')

    if commit_count == 0 or first_commit == None:
        thread_print(Fore.YELLOW + f'Skipping repository {repo_full_name}, could not get first commit or commit_count')
        return

    repo_snapshot_commits = get_snapshot_commits_optimized(
        repo_full_name, 
        commit_count,
        first_commit,
        dateutil.parser.parse(repository['updated_at']), 
        timedelta(days=90))

    if repo_snapshot_commits is None:
        thread_print(Fore.YELLOW + f'Skipping repository {repo_full_name}, could not get first commit')
        return

    repo_snapshot_trees = get_repo_trees(full_name=repo_full_name, commits=repo_snapshot_commits)

    for i in range(len(repo_snapshot_commits)):
        repo_snapshot_trees[i]['date'] = dateutil.parser.isoparse(repo_snapshot_commits[i]['commit']['author']['date'])
        repo_snapshot_trees[i]['sha'] = repo_snapshot_commits[i]['sha']
        repo_snapshot_trees[i]['repo_full_name'] = repo_full_name
        if 'url' in repo_snapshot_trees[i]:
            del repo_snapshot_trees[i]['url']

    if len(repo_snapshot_trees) == 0:
        thread_print(f'No trees found for {repo_full_name}')
        return

    stored_trees = find_tools_and_store_in_database({'full_name' : repo_full_name, 'default_branch' : repository['default_branch'], 'trees' : repo_snapshot_trees}, wrapper)

    stop = time.time()

    if (stored_trees):
        check_file_lock.acquire()

        parsed_repositories[repo_full_name] = {'trees' : len(repo_snapshot_trees), 'time' : stop - start}

        check_file_lock.release()
    else:
        thread_print(Fore.RED + f'Failed to store trees for {repo_full_name}')



def set_interrupted_flag_and_cancel_futures(connection: multiprocessing.connection.Connection) -> None:
    global interrupted, interrupt_number, futures, saver_thread
    if connection is None:
        return
    _ = connection.recv()
    thread_print(Fore.YELLOW + f'Interrupt received (time: {datetime.now()}), stopping after current repository' + Style.RESET_ALL)
    interrupted.set()
    for future in futures:
        future.cancel()
    _ = connection.recv()
    thread_print(Fore.RED + f'Interrupt received (time: {datetime.now()}), saving check file and exiting' + Style.RESET_ALL)
    saver_thread_killed.set()
    time.sleep(5)
    save_check_file()
    for future in futures:
        future.terminate()
    os._exit(0)

def check_database() -> None:
    wrapper = MongoDBWrapper()
    error = False
    with open(CHECK_FILE_PATH, 'r') as check_file:
        for line in check_file:
            check = json.loads(line)
            repo_full_name = check['repo_full_name']
            tree_count = check['trees']
            repo_history_count = wrapper.count_repo_snapshots(repo_full_name)
            if tree_count != repo_history_count:
                error = True
                thread_print(f'{repo_full_name} has {tree_count} trees in the check file and {repo_history_count} trees in the database')
    if not error:
        thread_print(Fore.GREEN + 'Database check completed successfully')
    else:
        thread_print(Fore.RED + 'Database check failed')

def sanity_check() -> None:
    wrapper = MongoDBWrapper()
    with open(CHECK_FILE_PATH, 'r') as check_file:
        for line in check_file:
            check = json.loads(line)
            repo_full_name = check['repo_full_name']
            tree_count = check['trees']
            repo = wrapper.get_repositories(filter={"full_name": repo_full_name}, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0})[0]
            trimester_count = dateutil.parser.parse(repo['updated_at']).year * 4 + (dateutil.parser.parse(repo['updated_at']).month - 1) // 3 - dateutil.parser.parse(repo['created_at']).year * 4 - (dateutil.parser.parse(repo['created_at']).month - 1) // 3 + 1
            # Check if same vicinity
            if tree_count / trimester_count > 1.5 or trimester_count / tree_count > 1.5:
                thread_print(f'{repo_full_name} has {tree_count} trees and {trimester_count} trimesters')

def test_github_api_limits(repositories : Cursor) -> None:
    repositories_list = list(repositories)
    its = 0
    while True:
        for repository in repositories_list:
            get_repo(repository['full_name'])
            its += 1
            if its % 100 == 0:
                thread_print(f'Performed {its} requests')

interrupt_at = None

def raise_sigint() -> None:
    signal.raise_signal(signal.SIGINT)

def save_check_file() -> None:
    global parsed_repositories, check_file_lock
    with open(CHECK_FILE_PATH, 'w') as check_file:
        check_file_lock.acquire()
        for repo_full_name, repo_info in parsed_repositories.items():
            check_file.write(json.dumps({'repo_full_name' : repo_full_name, 'trees' : repo_info['trees'], 'time' : repo_info['time']}) + '\n')
        check_file_lock.release()

def save_check_file_every_5_seconds() -> None:
    thread_print(Fore.YELLOW + 'Saving check file every 5 seconds')
    while not saver_thread_killed.is_set():
        save_check_file()
        if interrupted.is_set() and all_threads_done.is_set():
            thread_print(Fore.GREEN + 'All threads done, exiting safely')
            break
        time.sleep(5)
    return

def retrieve_tool_histories(receiver, delete_tools, _check_database, _sanity_check, _test_github_api_limits, _delete_check_file, stop_if_no_sample, _check_file_path):
    global interrupt_at, CHECK_FILE_PATH, saver_thread
    CHECK_FILE_PATH = _check_file_path

    wrapper = MongoDBWrapper()

    # if parser.parse_args().interrupt_at is not None:
    #     interrupt_at = datetime.strptime(parser.parse_args().interrupt_at, '%Y-%m-%dT%H:%M')
    #     alarm_time = (interrupt_at - datetime.now()).total_seconds()
    #     thread_print(Fore.YELLOW + f'Interrupting at {interrupt_at}')
    #     timer = threading.Timer(alarm_time, raise_sigint)
    #     timer.daemon = True
    #     timer.start()
        
    if delete_tools:
        wrapper.delete_repo_histories()
        return
    
    if _check_database:
        thread_print(Fore.YELLOW + 'Checking database')
        check_database()
        return
    
    if _sanity_check:
        thread_print(Fore.YELLOW + 'Performing sanity check')
        sanity_check()
        return
    
    if _test_github_api_limits:
        thread_print(Fore.YELLOW + 'Testing GitHub API limits')
        filter = {}
        test_github_api_limits(wrapper.get_repositories(filter=filter, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0}))
        return
    
    if _delete_check_file:
        thread_print(Fore.RED + 'Deleting repository check file')
        thread_print("To delete the check file, type 'DELETE' and press enter")
        if os.path.exists(CHECK_FILE_PATH):
            os.remove(CHECK_FILE_PATH)

    initialize_parsed_repositories()

    sentinel_thread = threading.Thread(target=set_interrupted_flag_and_cancel_futures, args=[receiver], daemon=True)

    saver_thread = threading.Thread(target=save_check_file_every_5_seconds, daemon=True)

    sentinel_thread.start()
    saver_thread.start()

    while True:
        futures = []
        repositories = wrapper.get_random_processed_repositories(1000)

        if stop_if_no_sample and len(repositories) == 0:
            thread_print(Fore.GREEN + 'No more repositories to process')
            interrupted.set()
            all_threads_done.set()
            break

        all_threads_done.clear()

        try:
            executor = ThreadPoolExecutor(max_workers=16)

            for repository in repositories:
                f = executor.submit(get_repository_trees, repository, wrapper)
                futures.append(f)

            thread_print(f'Waiting for {len(futures)} futures to complete')

            wait(futures, return_when=ALL_COMPLETED)

            executor.shutdown()
        except KeyboardInterrupt:
            thread_print(Fore.YELLOW + 'Keyboard interrupt received')
            executor.shutdown()
            all_threads_done.set()
            break

        all_threads_done.set()

    thread_print('Waiting for saver thread to finish')
    saver_thread.join()

    sys.exit(0)
