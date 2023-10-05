import threading
import signal
import argparse

from github_api_wrappers import *
from mongodb_wrappers import *
from colorama import Fore, Style


# Command line arguments
parser = argparse.ArgumentParser(description='Load trees from GitHub repositories into MongoDB')

parser.add_argument('filter_file_path', nargs='?', type=str, default='', help='Path for JSON file with filter for the repositories to load trees from, if not specified all repositories will be used')
parser.add_argument('--delete-trees', action='store_true', help='Delete all trees from the trees collection')
parser.add_argument('--check-database', action='store_true', help='Check the database for inconsistencies with check file')
parser.add_argument('--delete-check-file', action='store_true', help='Delete the repository check file')

interrupt_number = 0
interrupted = threading.Event()

all_trees_retrieved = threading.Event()

tree_lock = threading.Lock()

trees = []

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

        # Convert the subtrees dictionary to a list and return it
        return list(subtrees.values())

def load_trees_into_database() -> None:
    global interrupted, all_trees_retrieved, trees, tree_lock
    wrapper = MongoDBWrapper()
    while True:
        tree_lock.acquire()

        length = len(trees)

        tree_lock.release()

        if all_trees_retrieved.is_set() and length == 0:
            print(Fore.BLUE + 'LOADER THREAD:\t' + Fore.GREEN + 'All trees stored, exiting safely' + Style.RESET_ALL)
            return
        
        # Wait until there are trees to load
        if length == 0:
            print(Fore.BLUE + 'LOADER THREAD:\t' + Fore.YELLOW + 'No trees to load, waiting 20 seconds' + Style.RESET_ALL)
            time.sleep(20)
            continue

        tree_lock.acquire()

        # Get the trees to load
        trees_to_load = trees[:5000]
        trees = trees[5000:]

        tree_lock.release()

        print(Fore.BLUE + 'LOADER THREAD:\t' + Style.RESET_ALL + f'Adding {len(trees_to_load)} trees to database')
        
        start = time.time()

        # Insert the trees into the database
        while True:
            try:                
                wrapper.add_trees(trees_to_load)
                break
            except Exception as e:
                print(e.details)
                print(Fore.BLUE + 'LOADER THREAD:\t' + Fore.RED + 'Retrying to add trees' + Style.RESET_ALL)
                continue        

        end = time.time()

        print(Fore.BLUE + 'LOADER THREAD:\t' + Style.RESET_ALL + f'Time taken to add {len(trees_to_load)} trees to database: {end - start}')

def get_repository_trees(repositories : Cursor) -> None:
    global interrupted, all_trees_retrieved, trees, tree_lock

    for repository in repositories:
        if interrupted.is_set():
            print(Fore.MAGENTA + 'GETTER THREAD:\t' + Fore.GREEN + 'Interrupted, exiting safely' + Style.RESET_ALL)
            break
        
        repo_full_name = repository['full_name']

        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Style.RESET_ALL + f'Processing repository: {repo_full_name}')

        start = time.time()

        commit_count = get_commits_count(repo_full_name)

        repo_snapshot_commits = get_snapshot_commits_optimized(
            repo_full_name, 
            commit_count, 
            dateutil.parser.parse(repository['created_at']), 
            dateutil.parser.parse(repository['updated_at']), 
            timedelta(days=90)) # TODO Check interval

        end = time.time()

        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Style.RESET_ALL + f'Time taken to retrieve {len(repo_snapshot_commits)} snapshot commits: {end - start}')

        start = time.time()

        repo_snapshot_trees = get_repo_trees(full_name=repo_full_name, commits=repo_snapshot_commits)

        end = time.time()

        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Style.RESET_ALL + f'Time taken to retrieve {len(repo_snapshot_trees)} snapshot trees: {end - start}')

        for i in range(len(repo_snapshot_commits)):
            repo_snapshot_trees[i]['date'] = dateutil.parser.isoparse(repo_snapshot_commits[i]['commit']['author']['date'])
            repo_snapshot_trees[i]['repo_full_name'] = repo_full_name
            del repo_snapshot_trees[i]['url']

        if len(repo_snapshot_trees) == 0:
            print(Fore.MAGENTA + 'GETTER THREAD:\t' + Style.RESET_ALL + f'No trees found for {repo_full_name}')
            continue

        repo_snapshot_subtrees = []

        for tree in repo_snapshot_trees:
            repo_snapshot_subtrees.extend(split_tree_into_subtrees(tree))

        with open('repository_check_file', 'a') as check_file:
            check_file.write(f'{{ "repo_full_name" : "{repo_full_name}", "trees" : {len(repo_snapshot_subtrees)} }}\n')

        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Style.RESET_ALL + f'Adding {len(repo_snapshot_trees)} trees ({len(repo_snapshot_subtrees)} subtrees) from {repo_full_name} to loading queue')

        tree_lock.acquire()

        trees.extend(repo_snapshot_subtrees)

        tree_lock.release()

    all_trees_retrieved.set()
    print(Fore.MAGENTA + 'GETTER THREAD:\t' + Fore.GREEN + 'All repositories retrieved, exiting safely' + Style.RESET_ALL)

def set_interrupted_flag(_signal, _frame) -> None:
    global interrupted, interrupt_number
    interrupt_number += 1
    if interrupt_number == 1:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.YELLOW + 'Interrupted once, stopping after current repository' + Style.RESET_ALL)
        interrupted.set()
    elif interrupt_number == 2:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + 'Interrupted again, stopping immediately' + Style.RESET_ALL)
        os._exit(1)

def check_database() -> None:
    wrapper = MongoDBWrapper()
    error = False
    with open('repository_check_file', 'r') as check_file:
        for line in check_file:
            check = json.loads(line)
            repo_full_name = check['repo_full_name']
            tree_count = check['trees']
            database_tree_count = wrapper.count_repo_trees(repo_full_name)
            if tree_count != database_tree_count:
                error = True
                print(f'{repo_full_name} has {tree_count} trees in the check file and {database_tree_count} trees in the database')
    if not error:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.GREEN + 'Database check completed successfully' + Style.RESET_ALL)
    else:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + 'Database check failed' + Style.RESET_ALL)

def main():    
    wrapper = MongoDBWrapper()

    if parser.parse_args().delete_trees:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + 'Deleting all trees from the trees collection' + Style.RESET_ALL)
        print("To delete all trees from the trees collection, type 'DELETE' and press enter")
        if input() == 'DELETE':
            wrapper.delete_all_trees()
        return
    
    if parser.parse_args().check_database:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.YELLOW + 'Checking database' + Style.RESET_ALL)
        check_database()
        return
    
    if parser.parse_args().delete_check_file:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + 'Deleting repository check file' + Style.RESET_ALL)
        os.remove('repository_check_file')

    signal.signal(signal.SIGINT, set_interrupted_flag)

    filter = {}

    if parser.parse_args().filter_file_path != '':
        with open(parser.parse_args().filter_file_path, 'r') as filter_file:
            filter = json.load(filter_file)

    cursor = wrapper.get_repositories(filter=filter, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0})

    getter_thread = threading.Thread(target=get_repository_trees, kwargs={'repositories': cursor})
    loader_thread = threading.Thread(target=load_trees_into_database)

    getter_thread.start()
    loader_thread.start()

    while getter_thread.is_alive():
        getter_thread.join(5)

    while loader_thread.is_alive():
        loader_thread.join(5)

if __name__ == '__main__':
    main()