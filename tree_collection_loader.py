from github_api_wrappers import *
from mongodb_wrappers import *

# repo_full_names = get_repository_full_names(per_page=5)

wrapper = MongoDBWrapper()

def create_indexes() -> None:
    wrapper.db.trees.create_index("repo_full_name", unique=True)
    wrapper.db.trees.create_index("date")

def load_repository_trees(filter : dict = {}) -> None:
    repositories = wrapper.get_repositories(filter=filter, projection={"full_name": 1, "created_at": 1, "updated_at": 1, "_id": 0})

    for repository in repositories:
        repo_full_name = repository['full_name']

        print(f'Processing repository: {repo_full_name}')


        start = time.time()

        commit_count = get_commits_count(repo_full_name)

        repo_snapshot_commits = get_snapshot_commits_optimized(
            repo_full_name, 
            commit_count, 
            dateutil.parser.parse(repository['created_at']), 
            dateutil.parser.parse(repository['updated_at']), 
            timedelta(days=90))

        end = time.time()

        print(f'Time taken to retrieve {len(repo_snapshot_commits)} snapshot commits: {end - start}')

        start = time.time()

        repo_snapshot_trees = get_repo_trees(full_name=repo_full_name, commits=repo_snapshot_commits)

        end = time.time()

        print(f'Time taken to retrieve {len(repo_snapshot_trees)} snapshot trees: {end - start}')

        for i in range(len(repo_snapshot_commits)):
            repo_snapshot_trees[i]['date'] = repo_snapshot_commits[i]['commit']['author']['date']
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


def main(*args, **kwargs):
    load_repository_trees()    

main()