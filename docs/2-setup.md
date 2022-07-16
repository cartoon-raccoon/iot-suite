# Setup and Configuration

Setting up IoTSuite is fairly straightforward. Everything is defined in the configuration file, and IoTSuite itself is fairly flexible in allowing for different set-up configurations.

## System Requirements

IoTSuite only runs on Linux. It is recommended to have at least kernel version 5.10.

The following external programs are required for IoTSuite to work:

- A Python 3 interpreter
- QEMU, a system emulator
- `iproute`, providing the `ip` command
- `sudo`
- `buildroot`, if building the VM images

## Obtaining the VM images

The sandbox VMs are compiled using Buildroot, a build system built on GNU Make that takes an auto-generated configuration file and compiles a completely custom embedded Linux system for each architecture. The config files for each architecture can be found in the `configs` directory.

The CNC VM is a standard Ubuntu Server distribution, installed to a disk image file supported by QEMU. Currently IoTSuite only supports the QCOW2 format.

### Self-Compiling the Sandboxes

TODO

## Directory Structure

Each architecture has its own directory where the VM image is stored. This can be any directory in any part of the filesystem, as long as the user has access rights. However, due to the way Buildroot compiles the images for a QEMU target, each directory needs the following required files for each embedded architecture (i.e. ARM, MIPS, etc.):

- `kernel.img`. This is the compiled kernel.
- `rootfs.qcow2`. This is the root filesystem image. All the required scripts and tools are already installed within the filesystem due to Buildroot's filesystem overlay functionality.

ARM requires an additional file: `versatile-pb.dtb`. This is the Device Tree Blob (DTB) file required by QEMU when starting the system.

These filenames *must* be named as given; these names are hardcoded into IoTSuite. (See `arch.py` in the source code for details.)

Similarly, the CNC VM image uses its own directory, and is treated as its own architecture by IoTSuite. The following files are required:

- `rootfs.qcow2`. This is the root filesystem, with the kernel installed within it.

## CNC VM Setup

While the sandbox VMs may be already set up, setting up the CNC VM requires some additional work. A shell script is provided to start up the CNC VM with internet access, allowing the user to update the system and install the required tools.

TODO - installing cowrie, setting up SSH, disabling resolved, enabling fakedns

## Installing the Source Code

IoTSuite is a Python program, and thus can run on any Linux machine with a Python 3 interpreter.

IoTSuite requires the following Python libraries:

- `python-magic` - a Python wrapper for libmagic
- `pyelftools` - native Python library for parsing ELF files
- `pexpect` - library for interacting with programs through stdin
- `fabric` - library for SSH communication on Python
- `invoke` - library for invoking shell commands
