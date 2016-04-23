# Simple multi-ssh tool, for running remote commands in parallel over ssh.
#
# It will use execute up to 10 ssh processes at a time, executing the given
# shell command once on each remote host and printing the output.
#
# Call this script simply by hosts and a command:
#
#   python mussh.py host1,host2,host3 "uname -a"

from sys import argv
from qpipe import Iter, Exec, Print
from subprocess import check_output

if __name__ == '__main__':
    if len(argv) <= 1:
        print("Usage: %s hostnames(comma-separated) command", argv[0])
    hosts = argv[1].split(",")
    command = argv[2]

    ssh_commands = []
    for h in hosts:
        ssh_commands.append(["ssh", h, command])
    Iter(ssh_commands).into(Exec(processes=10)).into(Print()).execute()
