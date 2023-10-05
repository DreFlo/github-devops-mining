import threading
import signal
import argparse

from github_api_wrappers import *
from mongodb_wrappers import *
from colorama import Fore, Style


# Command line arguments
parser = argparse.ArgumentParser(description='Load trees from GitHub repositories into MongoDB')

parser.add_argument('--delete-trees', action='store_true', help='Delete all trees from the trees collection')


interrupted = threading.Event()

all_trees_retrieved = threading.Event()

tree_lock = threading.Lock()

trees = []

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
        trees_to_load = trees[:50]
        trees = trees[50:]

        tree_lock.release()

        print(Fore.BLUE + 'LOADER THREAD:\t' + Style.RESET_ALL + f'Adding {len(trees_to_load)} trees to database')

        tries = 0
        
        start = time.time()

        # Insert the trees into the database
        while not (tries != 0 and interrupted.is_set()):
            try:                
                wrapper.add_trees(trees_to_load)
                break
            except Exception as e:
                print(e.details)
                print(Fore.BLUE + 'LOADER THREAD:\t' + Fore.RED + 'Retrying to add trees' + Style.RESET_ALL)
                tries += 1
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

        print(Fore.MAGENTA + 'GETTER THREAD:\t' + Style.RESET_ALL + f'Adding {len(repo_snapshot_trees)} trees from {repo_full_name} to loading queue')

        tree_lock.acquire()

        trees.extend(repo_snapshot_trees)

        tree_lock.release()

    all_trees_retrieved.set()

def set_interrupted_flag(_signal, _frame) -> None:
    global interrupted
    print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + 'Interrupted, stopping after current repository or at error' + Style.RESET_ALL)
    interrupted.set()

def main():    
    wrapper = MongoDBWrapper()

    if parser.parse_args().delete_trees:
        print(Fore.LIGHTCYAN_EX + 'MAIN THREAD:\t' + Fore.RED + 'Deleting all trees from the trees collection' + Style.RESET_ALL)
        wrapper.db.trees.delete_many({})

    signal.signal(signal.SIGINT, set_interrupted_flag)

    cursor = wrapper.get_repositories(filter={}, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0})

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