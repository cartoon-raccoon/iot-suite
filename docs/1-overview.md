# Introduction

Welcome to the documentation for the IoTSuite project! This set of documents aims to provide an understanding of the objectives and design of IoTSuite, as well as its capabilities and limitations. It also provides information on how to set up, configure, and invoke IoTSuite.

## What is IoTSuite?

IoTSuite is a malware sandbox tailored exclusively to the testing and reversing of Internet-of-Things (IoT) malware. Since this malware runs primarily on embedded Linux systems, IoTSuite operates on a Linux system, and runs only Linux malware. It can theoretically handle any executable file, from scripts to binary executables, but it works best with executable ELF files.

IoTSuite is extremely flexible and easily extensible, as it is written in Python and highly decoupled. As such, additional functionality can be easily added. In addition, it can dynamically import user plugins to run custom code on the data collected from running the malware sample.

## Capabilities

IoTSuite can handle executables compiled for most embedded architectures. It currently supports:

- ARM 32-bit
- MIPS 32-bit
- MIPSEL 32-bit
- PowerPC
- M68000
- i386
- x86_64

However, additional architectures can be easily added. Each architecture has its own virtual machine image and is automatically spun up by IoTSuite.

IoTSuite collects data on the two main domains of malware analysis: static and dynamic analysis. Firstly, it automatically calculates the SHA256 digest and context-triggered piecewise hashes of the sample, as well as automatically detecting the architecture that the malware sample is compiled for, and running the corresponding VM. It can also detect basic UPX packing and extract strings from the sample.

In the dynamic domain, IoTSuite collects data on network activity, filesystem changes, and system calls made by the sample. It leverages existing tools that have been custom-compiled for the VM, such as `dumpcap`, `strace`, and `inotify` to extract this data. This data is then extracted from the VM and can be analysed by custom user scripts.

## Limitations

However, IoTSuite is not without its limitations. These include:

- IoTSuite cannot redirect IP addresses to allow the fake CNC server to respond. It currently relies on a fake DNS server running on the fake CNC to spoof DNS queries. This is due to problems in the implementation of `iptables` and the `nfqueue` libraries. This problem is being actively worked on and IoTSuite will soon have this capability.

- IoTsuite is not efficient when running on batches of samples. This is because each sample is run synchronously, as opposed to multiple samples simultaneously. This is due to limitations in the network infrastructure required to cater to each sample. However, this is the limiting factor in enabling this functionality and once a suitable implementation of the network infrastructure is found, this functionality can be easily added.

## Architecture

IoTSuite has the following architecture:

[todo: insert image here]

It relies on a custom network infrastructure, and two main virtual machines running on QEMU, a system emulator. Firstly, the sandbox VM. This is a custom embedded Linux system built using Buildroot (more info in Setup). This is where the malware sample is run, and an orchestrator Python script runs locally on this machine to coordinate the analysis process. Secondly, the CNC VM. This is a standard Linux server distribution.

The network architecture is also custom-built for IoTSuite. It makes use of a network bridge to connect two network tap devices created by QEMU when invoked. This creates an isolated network environment disconnected from the Internet, but can still be accessed from the host machine. `dhcpd`, a DHCP server, runs on the host machine to assign IP addresses to each guest machine. These addresses are directly linked to the MAC addresses of each VM, hence each VM will receive the same IP address every time.

The fake CNC serves as a honeypot system to initiate malicious behaviour from the sample. It runs Cowrie, a Telnet and SSH honeypot system, to log malicious activity such as command injection. It also funs FakeDNS, a Python script to spoof DNS responses. This is to allow network requests to be redirected to the fake CNC VM. Unfortunately, due to limitations in `iptables`, direct IP redirection is currently unsupported, but will be implemented in the future.
