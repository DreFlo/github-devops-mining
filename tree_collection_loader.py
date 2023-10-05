import threading
import signal
import argparse

from github_api_wrappers import *
from mongodb_wrappers import *
from colorama import Fore, Style

# repo_full_names = get_repository_full_names(per_page=5)

wrapper = MongoDBWrapper()

interrupted = threading.Event()

parser = argparse.ArgumentParser(description='Load trees from GitHub repositories into MongoDB')

parser.add_argument('--create-indexes', action='store_true', help='Create indexes on the trees collection')

parser.add_argument('--delete-trees', action='store_true', help='Delete all trees from the trees collection')

def load_repository_trees(filter : dict = {}) -> None:
    global interrupted
    repositories = wrapper.get_repositories(filter=filter, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0})

    for repository in repositories:
        if interrupted.is_set():
            print(Fore.GREEN + 'Interrupted, exiting safely' + Style.RESET_ALL)
            return
        
        repo_full_name = repository['full_name']

        print(f'Processing repository: {repo_full_name}')

        start = time.time()

        commit_count = get_commits_count(repo_full_name)

        repo_snapshot_commits = get_snapshot_commits_optimized(
            repo_full_name, 
            commit_count, 
            dateutil.parser.parse(repository['created_at']), 
            dateutil.parser.parse(repository['updated_at']), 
            timedelta(days=90)) # TODO Check interval

        end = time.time()

        print(f'Time taken to retrieve {len(repo_snapshot_commits)} snapshot commits: {end - start}')

        start = time.time()

        repo_snapshot_trees = get_repo_trees(full_name=repo_full_name, commits=repo_snapshot_commits)

        end = time.time()

        print(f'Time taken to retrieve {len(repo_snapshot_trees)} snapshot trees: {end - start}')

        for i in range(len(repo_snapshot_commits)):
            repo_snapshot_trees[i]['date'] = dateutil.parser.isoparse(repo_snapshot_commits[i]['commit']['author']['date'])
            repo_snapshot_trees[i]['repo_full_name'] = repo_full_name
            del repo_snapshot_trees[i]['url']

        if len(repo_snapshot_trees) == 0:
            print(f'No trees found for {repo_full_name}')
            continue

        print(f'Adding {len(repo_snapshot_trees)} trees from {repo_full_name} to database')

        start = time.time()

        wrapper.add_trees(repo_snapshot_trees)

        end = time.time()

        print(f'Time taken to add {len(repo_snapshot_trees)} trees to database: {end - start}')

def set_interrupted_flag(_signal, _frame) -> None:
    global interrupted
    print(Fore.RED + 'Interrupted, stopping after current repository' + Style.RESET_ALL)
    interrupted.set()

def main():
    if parser.parse_args().delete_trees:
        print(Fore.RED + 'Deleting all trees from the trees collection' + Style.RESET_ALL)
        wrapper.db.trees.delete_many({})

    signal.signal(signal.SIGINT, set_interrupted_flag)

    loader_thread = threading.Thread(target=load_repository_trees, kwargs={'filter': {'full_name': 'facebook/react-native'}})

    loader_thread.start()

    while loader_thread.is_alive():
        loader_thread.join(5)

if __name__ == '__main__':
    main()