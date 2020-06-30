import sys
import time
import traceback
from subprocess import Popen

python_command = sys.argv[1]
filename = sys.argv[2]

sleep_after_error = 10

command = '{} {}'.format(python_command, filename)

while True:
    try:
        print(f'Starting {filename}')
        p = Popen(command, shell=True)
        p.wait()
    except:
        err = traceback.format_exc()
        print(f'{filename} failed:\n{err}')
        print(f'Restarting {filename} in {sleep_after_error} seconds.')
        time.sleep(sleep_after_error)
