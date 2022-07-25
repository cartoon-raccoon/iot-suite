# iotsuite

_A Linux malware sandbox_

A Linux IOT malware sandbox designed for concurrency and bulk analysis.

### System Requirements

- QEMU, a full system emulator for all sorts of architectures
- `iptables`, an interface to the Linux kernel's `netfilter` module
- `dhcpd`, a lightweight DHCP server
- Python 3.7 and above
- Bash 5.1 and above

### Build Requirements

- Buildroot, a build system geared for creating embedded Linux systems (use the submodule in this repo, it contains required Perl modules)

The documentation can be found [here](docs/1-overview.md).

To clone this repository, run:

```text
git clone https://github.com/cartoon-raccoon/iot-suite.git
```

You will then need to initialize the submodules within the repository. Change into the project directory and run:

```text
git submodule init
```

IoTSuite requires Buildroot images and an Ubuntu QCOW2 image with certain packages installed. The Buildroot configuration files for each architecture can found in the `configs/` directory. Simply copy them to the `buildroot/` submodule directory as `.config` and run `make BR2_EXTERNAL=/path/to/iotsuite/br-external`.
