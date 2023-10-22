import os
from colorama import Fore, Style
import threading

def thread_print(*args, **kwargs):
    print(f'{os.getpid()}' + Fore.LIGHTCYAN_EX if threading.current_thread().name == 'MainThread' else Fore.MAGENTA + f' {threading.current_thread().name}:' + Style.RESET_ALL, end='\t')
    print(*args, **kwargs)
    print(Style.RESET_ALL, end='')