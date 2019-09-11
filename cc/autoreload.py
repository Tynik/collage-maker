import os
import sys
import time
import signal
import subprocess


def file_filter(name):
    return name != '__pycache__' and not name.endswith('.pyc')


def file_times(path):
    for file in filter(file_filter, os.listdir(path)):
        yield os.stat(os.path.join(path, file)).st_mtime


path, command = sys.argv[1], ' '.join(sys.argv[2:])
process = subprocess.Popen(command, shell=True)
last_mtime = max(file_times(path))
while True:
    max_mtime = max(file_times(path))
    if process.stdout is not None:
        print(process.stdout)

    if max_mtime > last_mtime:
        last_mtime = max_mtime
        print('Restarting process...')
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process = subprocess.Popen(command, shell=True)

    time.sleep(1)
