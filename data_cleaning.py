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

interrupt_number = 0
interrupted = threading.Event()

futures = []

def check_tools_dates(tool_history, _ : MongoDBWrapper):
    tool_launch_dates = {
        "Agola" : datetime(2019, 7, 15),
        "AppVeyor" : datetime(2011, 1, 1),
        "ArgoCD" : datetime(2018, 3, 13),
        "Bytebase" : datetime(2021, 7, 9),
        "Cartographer" : datetime(2021, 9, 21),
        "CircleCI" : datetime(2011, 1, 1),
        "Cloud 66 Skycap" : datetime(2017, 12, 7),
        "Cloudbees Codeship" : datetime(2011, 1, 1),
        "Devtron" : datetime(2021, 4, 7),
        "Flipt" : datetime(2019, 2, 16),
        "GitLab" : datetime(2012, 10, 22),
        "Google Cloud Build" : datetime(2016, 1, 14),
        "Helmwave" : datetime(2020, 10, 2),
        "Travis" : datetime(2011, 1, 1),
        "Jenkins" : datetime(2011, 2, 3),
        "JenkinsX" : datetime(2018, 3, 19),
        "Keptn" : datetime(2021, 5, 21),
        "Liquibase" : datetime(2006, 1, 1),
        "Mergify" : datetime(2018, 8, 1),
        "OctopusDeploy" : datetime(2011, 10 ,7),
        "OpenKruise" : datetime(2019, 7, 17),
        "OpsMx" : datetime(2017, 9, 1),
        "Ortelius" : datetime(2023, 2, 13),
        "Screwdriver" : datetime(2017, 1, 12),
        "Semaphore" : datetime(2012, 1, 1),
        "TeamCity" : datetime(2006, 1, 1),
        "werf" : datetime(2017, 8, 22),
        "Woodpecker CI" : datetime(2019, 4, 6),
        "Codefresh" : datetime(2014, 1, 1),
        "XL Deploy" : datetime(2008, 1, 1),
        "Drone" : datetime(2014, 1, 1),
        "Flagger" : datetime(2018, 10, 7),
        "Harness.io" : datetime(2016, 1, 1),
        "Flux" : datetime(2016, 10, 28),
        "GoCD" : datetime(2007, 1, 1),
        "Concourse" : datetime(2015, 1, 27),
        "Kubernetes" : datetime(2014, 10, 15),
        "GitHubActions" : datetime(2018, 10, 16),
        "AWS CodePipeline" : datetime(2015, 7, 9),
    }

    clean_history = {'repo_full_name' : tool_history['repo_full_name'], 'snapshots' : []}

    for snapshot in tool_history['snapshots']:
        error = False
        for tool in snapshot['tools']:
            if snapshot['date'] < tool_launch_dates[tool]:
                error = True
                break
        if not error:
            clean_history['snapshots'].append(snapshot)

    return clean_history

def retry_no_tree_founds(tool_history, _ : MongoDBWrapper):
    clean_history = {'repo_full_name' : tool_history['repo_full_name'], 'snapshots' : []}

    for snapshot in tool_history['snapshots']:
        new_snapshot = snapshot
        if 'warning' in snapshot:
            tree = get_repo_tree(tool_history['repo_full_name'], snapshot['sha'])
            tree['date'], tree['sha'] = snapshot['date'], snapshot['sha']
            new_snapshot = find_repo_trees_tools(tool_history['repo_full_name'], '', [tree])[0]
        clean_history['snapshots'].append(new_snapshot)

    return clean_history


def clean_snapshot_times(tool_history, wrapper : MongoDBWrapper):
    clean_history = {'repo_full_name' : tool_history['repo_full_name'], 'snapshots' : []}

    last_snapshot = wrapper.db['random'].find_one({'full_name' : tool_history['repo_full_name']}, {'tree', 'tools_used'})

    last_snapshot_sha = last_snapshot['tree'].split('/')[-1]

    last_snapshot_date = dateutil.parser.isoparse(get_commit(tool_history['repo_full_name'], last_snapshot_sha)['commit']['author']['date'])

    for snapshot in sorted(tool_history['snapshots'], key=lambda snap:snap['date']):
        if snapshot['date'] < datetime(2012, 1, 1):
            continue

        if snapshot['date'] >= last_snapshot_date or snapshot['sha'] == last_snapshot_sha or snapshot['date'] > datetime(2023, 10, 31):
            break

        clean_history['snapshots'].append(snapshot)

    if last_snapshot_date < datetime(2023, 10, 31):
        clean_history['snapshots'].append({'date' : last_snapshot_date, 'sha' : last_snapshot_sha, 'tools' : last_snapshot['tools_used']})

    return clean_history

def apply_function_chain(obj, wrapper : MongoDBWrapper, funcs):
    res = obj
    for func in funcs:
        res = func(res, wrapper)
        if res is None:
            return None
    return res

def clean_tool_history(tool_history, wrapper : MongoDBWrapper):
    clean_functions = [clean_snapshot_times, retry_no_tree_founds, check_tools_dates]
    cleaned_tool_history = apply_function_chain(tool_history, clean_functions)
    if cleaned_tool_history and not wrapper.has_been_cleaned(tool_history['repo_full_name']):
        #wrapper.add_clean_repo_history(clean_history=cleaned_tool_history)
        print(json.dumps(cleaned_tool_history, indent=2))

def set_interrupted_flag_and_cancel_futures(connection: multiprocessing.connection.Connection) -> None:
    global interrupted, interrupt_number, futures
    if connection is None:
        return
    _ = connection.recv()
    thread_print(Fore.YELLOW + f'Interrupt received (time: {datetime.now()}), stopping after current repository' + Style.RESET_ALL)
    interrupted.set()
    for future in futures:
        future.cancel()
    _ = connection.recv()
    thread_print(Fore.RED + f'Interrupt received (time: {datetime.now()}), saving check file and exiting' + Style.RESET_ALL)
    for future in futures:
        future.terminate()
    os._exit(0)

def main(receiver):
    wrapper = MongoDBWrapper()

    sentinel_thread = threading.Thread(target=set_interrupted_flag_and_cancel_futures, args=[receiver], daemon=True)
    sentinel_thread.start()

    histories = wrapper.get_random_processed_repositories(10)

    print(len(histories))

    while True:
        futures = []
        repositories = wrapper.get_random_processed_repositories(1000)

        if len(repositories) == 0:
            thread_print(Fore.GREEN + 'No more repositories to process')
            interrupted.set()
            break

        try:
            executor = ThreadPoolExecutor(max_workers=16)

            for repository in repositories:
                f = executor.submit(get_repository_trees, repository, wrapper)
                futures.append(f)

            thread_print(f'Waiting for {len(futures)} futures to complete')

            wait(futures, return_when=ALL_COMPLETED, timeout=(5 * 3600)) # Timeout 5h

            for future in futures:
                if not future.done():
                    future.terminate()

            executor.shutdown(cancel_futures=True)
        except KeyboardInterrupt:
            thread_print(Fore.YELLOW + 'Keyboard interrupt received')
            executor.shutdown()
            break

    for history in histories:
        print(history)
        print()
        clean_tool_history(history, wrapper)

if __name__ == "__main__":
    main()