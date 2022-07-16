#!/usr/bin/python

#!!!!! DO NOT RUN THIS ON THE HOST MACHINE

import os
import subprocess
from subprocess import PIPE
import sys
import time
import logging
import re

MINUTES_TO_RUN = 1
SECONDS_TO_RUN = MINUTES_TO_RUN * 60

logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)

logger.setLevel(logging.DEBUG)

processes = dict()

clean_ls = os.listdir()

def kill(pid):
    subprocess.run(["/bin/kill", "-s", "sigkill", f"{pid}"], 
        stdout=PIPE, stderr=PIPE
    )

def main():
    # get the file to analyse and restrict filename to 8 characters
    f = sys.argv[1]

    usef = f[:8] if len(f) > 8 else f

    # run dumpcap
    dumpcap_args = [
        "/usr/bin/dumpcap",
        "-a", f"duration:{SECONDS_TO_RUN}", "-P",
        "-w", f"{usef}.pcap",
    ]
    logger.debug(f"debug: spawning dumpcap with args {dumpcap_args}")
    dumpcap = subprocess.Popen(dumpcap_args, stdout=PIPE, stderr=PIPE)
    dumpcap_pid = dumpcap.pid
    processes["dumpcap"] = dumpcap
    logger.debug("debug: dumpcap successfully spawned")

    # run strace
    strace_args = [
        "/usr/bin/strace",
        # output to file strace_<truncated_file>.<pid>
        "-o", f"strace_{usef}",
        "-ff", f"./{f}"
    ]
    logger.debug(f"debug: spawning strace with args {strace_args}")
    strace = subprocess.Popen(strace_args, stdout=PIPE, stderr=PIPE)
    strace_pid = strace.pid
    processes["strace"] = strace
    logger.debug("debug: strace successfully spawned")

    logger.debug("debug: running sample")

    for i in range(SECONDS_TO_RUN):
        print(f"Seconds left: {SECONDS_TO_RUN - i}\r", end="")
        time.sleep(1)
    
    # terminate dumpcap and strace, wait and reap their exitcodes
    # if terminate did not work, kill it
    for name, proc in processes.items():
        if proc.poll() is None:
            proc.terminate()
            if proc.poll() is None:
                proc.kill()
        processes[name] = proc.wait()

    # last resort to kill via PID
    kill(dumpcap_pid)
    kill(strace_pid)

    # set up for checking strace output files
    stracefile_re = re.compile(f"^strace_{usef}\.[0-9]+$")
    export_files = []

    # check for files produced by strace and kill the associated pids
    for file in filter(lambda s: stracefile_re.match(s) is not None, os.listdir()):
        pid = file.split(".")[1]
        kill(pid)

    # iterate over the new files and filter out those that are not new
    for file in os.listdir():
        if file not in clean_ls:
            export_files.append(file)

    logger.debug("clearing iptables")
    subprocess.run(["iptables", "-F"])

    # output file names to be retrieved by iotftp
    print("\n===== LIST OF FILES TO RETRIEVE =====")
    for file in export_files:
        print(file)
    print("===== END LIST =====\n")

    
if __name__ == "__main__":
    main()