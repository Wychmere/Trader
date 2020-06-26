import sys
from subprocess import Popen

python_command = sys.argv[1]
filename = sys.argv[2]

while True:
    command = '{} {}'.format(python_command, filename)
    print(f'Starting {filename}')
    p = Popen(command, shell=True)
    p.wait()
