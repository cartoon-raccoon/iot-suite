#!/usr/bin/python

#!!!!! DO NOT RUN THIS ON THE HOST MACHINE

import subprocess
import sys
import logging

MINUTES_TO_RUN = 1
SECONDS_TO_RUN = MINUTES_TO_RUN * 60

processes = dict()

def main():
    # spawn inetsim and add it to the process management dict
    #! if we spawn inetsim as a system service, remove this line
    inetsim = subprocess.Popen(["/usr/bin/inetsim"])
    processes["inetsim"] = inetsim

    # get the file to analyse and restrict filename to 8 characters
    f = sys.argv[1]

    usef = f[:8] if len(f) > 8 else f

    # run dumpcap
    dumpcap_args = [
        "/usr/bin/dumpcap",
        "-a", "duration:60",
        "-w", f"{usef}.pcapng",
    ]
    dumpcap = subprocess.Popen(dumpcap_args)
    processes["dumpcap"] = dumpcap

    # construct strace args
    strace_args = [
        "/usr/bin/strace",
        # output to file strace_<truncated_file>.<pid>
        "-o", f"strace_{usef}",
        "-ff", f
    ]
    strace = subprocess.Popen(strace_args)
    processes["strace"] = strace

if __name__ == "__main__":
    main()