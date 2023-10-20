import subprocess
import argparse
import time
import signal

from datetime import datetime


parser = argparse.ArgumentParser(description='Load trees from GitHub repositories into MongoDB')
parser.add_argument('--delete-check-file', action='store_true', help='Delete the repository check file')
parser.add_argument('--interrupt-at', type=str, default=None, help='Interrupt the program at the specified time, format: YYYY-MM-DDTHH:MM')

subproc = None

def sigint_handler(_, __):
    print("Interrupted")
    subproc.kill(signal.SIGINT)

def main():
    global subproc
    interrupt_at = None
    if parser.parse_args().interrupt_at is not None:
        interrupt_at = datetime.strptime(parser.parse_args().interrupt_at, '%Y-%m-%dT%H:%M')

    subproc = subprocess.Popen(f'python .\\tree_collection_loader.py{" --delete-check-file" if parser.parse_args.delete_check_file else ""}')

    if interrupt_at:
        time.sleep((interrupt_at - datetime.now()).total_seconds())
        subproc.kill(signal.SIGINT)
    else:
        while True:
            time.sleep(1)
            

    return

if __name__ == '_main__':
    print("Com3")
    main()