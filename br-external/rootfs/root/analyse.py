#!/usr/bin/python

#!!!!! DO NOT RUN THIS ON THE HOST MACHINE

import os
import subprocess
from subprocess import PIPE
import time
import logging
import re
from argparse import ArgumentParser

logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)

processes = dict()

clean_ls = os.listdir()

ap = ArgumentParser()
ap.add_argument("file", type=str)
ap.add_argument("-t", "--timeout", action="store")
ap.add_argument("-x", "--disable", action="store")
ap.add_argument("-v", "--verbose", action="store_true")

def _parse_disable(s: str):
    if s == "none":
        return []
    return s.strip().split(",")

def kill(pid):
    if pid is None:
        return

    subprocess.run(["/bin/kill", "-s", "sigkill", f"{pid}"], 
        stdout=PIPE, stderr=PIPE
    )

def run_dumpcap(timeout, usef):
    # run dumpcap
    dumpcap_args = [
        "/usr/bin/dumpcap",
        "-a", f"duration:{timeout}", "-P",
        "-w", f"{usef}.pcap",
    ]
    logger.debug(f"debug: spawning dumpcap with args {dumpcap_args}")
    dumpcap = subprocess.Popen(dumpcap_args, stdout=PIPE, stderr=PIPE)
    processes["dumpcap"] = dumpcap
    logger.debug("debug: dumpcap successfully spawned")

    return dumpcap.pid

def run_strace(usef, f):
    # run strace
    strace_args = [
        "/usr/bin/strace",
        # string length
        "-s", "1024",
        # output to file strace_<truncated_file>.<pid>
        "-o", f"strace_{usef}",
        # timestamps
        "--timestamps=format:unix,precision:us",
        # follow forks
        "-ff",
        # the file to analyse
        f"./{f}"
    ]
    logger.debug(f"debug: spawning strace with args {strace_args}")
    strace = subprocess.Popen(strace_args, stdout=PIPE, stderr=PIPE)
    processes["strace"] = strace
    logger.debug("debug: strace successfully spawned")

    return strace.pid

def run_inotify():
    #todo
    pass

def cleanup(usef):
    # set up for checking strace output files
    stracefile_re = re.compile(f"^strace_{usef}\.[0-9]+$")
    # check for files produced by strace and kill the associated pids
    for file in filter(lambda s: stracefile_re.match(s) is not None, os.listdir()):
        pid = file.split(".")[1]
        kill(pid)

def main():
    # get the file to analyse and restrict filename to 8 characters
    args = ap.parse_args()

    f = args.file
    try:
        timeout = int(args.timeout)
    except:
        timeout = 60
    
    if args.disable is not None:
        disable = _parse_disable(args.disable)
    else:
        disable = []

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    usef = f[:8] if len(f) > 8 else f

    # capture start time
    start_time = time.time()

    if "dumpcap" not in disable:
        dumpcap_pid = run_dumpcap(timeout, usef)
    else:
        dumpcap_pid = None

    if "strace" not in disable:
        strace_pid = run_strace(usef, f)
    else:
        logger.warning("WARNING: strace is a critical part of analysis.")
        logger.warning("Disabling it will prevent this script from killing any spawned processes!")
        strace_pid = None

    if "inotify" not in disable:
        inotify_pid = run_inotify()
    else:
        inotify_pid = None
    
    logger.debug("debug: running sample")

    for i in range(timeout):
        print(f"Seconds left: {timeout - i}\r", end="")
        time.sleep(1)

    # capture end time
    end_time = time.time()
    
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
    kill(inotify_pid)

    export_files = []

    # if strace was disabled, just kill the VM
    # since the VM gets reset every run anyway
    if strace_pid is not None:
        cleanup(usef)

    # iterate over the new files and filter out those that are not new
    for file in os.listdir():
        if file not in clean_ls:
            export_files.append(file)

    logger.debug("clearing iptables")
    subprocess.run(["iptables", "-F"])

    # print out start and end times
    print("\n===== RESULTS =====")
    print(f"START TIME: {start_time}")
    print(f"END TIME: {end_time}")
    print("===== END RESULTS =====\n")

    # output file names to be retrieved by iotftp
    print("\n===== LIST OF FILES TO RETRIEVE =====")
    for file in export_files:
        print(file)
    print("===== END LIST =====\n")

    
if __name__ == "__main__":
    main()