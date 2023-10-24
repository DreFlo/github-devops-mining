import multiprocessing
import multiprocessing.connection
import argparse
import time
import sys
import atexit
import tree_collection_loader
import os

from datetime import datetime
from colorama import Fore, Style
from dotenv import load_dotenv


parser = argparse.ArgumentParser(description='Load trees from GitHub repositories into MongoDB')
parser.add_argument('--delete-tools', action='store_true', help='Delete all tools from the repo histories collection and exit')
parser.add_argument('--check-database', action='store_true', help='Check the database for inconsistencies with check file and exit')
parser.add_argument('--delete-check-file', action='store_true', help='Delete the repository check file')
parser.add_argument('--test-github-api-limits', action='store_true', help='Test the GitHub API limits and exit')
parser.add_argument('--sanity-check', action='store_true', help='Perform a sanity check on the database and exit')
parser.add_argument('--interrupt-at', type=str, default=None, help='Interrupt the program at the specified time, format: YYYY-MM-DDTHH:MM')
parser.add_argument('--stop-if-no-sample', action='store_true', help='Stop program if no sample of repos can be retrieved')
parser.add_argument('--env-file', type=str, default=None, help='Path to the .env file')
parser.add_argument('--check-file', type=str, default='repository_check_file', help='Path to the check file')

subproc = None

if parser.parse_args().env_file:
    load_dotenv(dotenv_path=parser.parse_args().env_file)
else:
    load_dotenv()

def kill_sub_proc_at_exit():
    global subproc
    if subproc:
        subproc.terminate()

def send_message_to_subproc_and_wait(sender : multiprocessing.connection.Connection):
    global subproc
    if subproc:
        sender.send("stop")
        print("Waiting for subproc")
        try:
            while subproc.is_alive():
                time.sleep(1)
            print("Subproc finished")
            subproc = None
        except KeyboardInterrupt:
            print("Interrupted")
            subproc = None
            sys.exit(0)

def main():
    global subproc
    interrupt_at = None

    atexit.register(kill_sub_proc_at_exit)

    if parser.parse_args().interrupt_at is not None:
        interrupt_at = datetime.strptime(parser.parse_args().interrupt_at, '%Y-%m-%dT%H:%M')

    delete_tools = False

    if parser.parse_args().delete_tools:
        print(Fore.RED + 'Deleting all tools from the repo histories collection' + Style.RESET_ALL)
        print("To delete all tools from the repo histories collection, type 'DELETE' and press enter")
        if input() == 'DELETE':
            delete_tools = True


    parsed_args = parser.parse_args()

    sender, receiver = multiprocessing.Pipe()

    args = (receiver, delete_tools, parsed_args.check_database, parsed_args.sanity_check, parsed_args.test_github_api_limits, parsed_args.delete_check_file, parsed_args.stop_if_no_sample, parsed_args.check_file)

    print(args)

    subproc = multiprocessing.Process(target=tree_collection_loader.retrieve_tool_histories, args=args, daemon=True)
    subproc.start()

    while True:
        try:
            if interrupt_at:
                time.sleep((interrupt_at - datetime.now()).total_seconds())
                print("Stopping subproc")
                send_message_to_subproc_and_wait(sender=sender)
                sys.exit(0)
            if subproc.is_alive():
                time.sleep(1)
            else:
                break
        except KeyboardInterrupt:
            print("Interrupted")
            send_message_to_subproc_and_wait(sender=sender)
            sys.exit(0)

    print(f"Subproc finished on its own - code: {subproc.exitcode} - at {datetime.now()}")

if __name__ == '__main__':
    main()