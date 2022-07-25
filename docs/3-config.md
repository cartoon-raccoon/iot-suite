# Configuration and Invocation

This section is concerned with the configuration and invocation of IoTSuite from the command line. Assuming IoTSuite is properly set up and configured, invocation should work properly.

## Configuration

IoTSuite is primarily configured via a `.conf` file. By default, this file is sourced from the `$XDG_CONFIG_HOME/iotsuite/` directory, but a custom configuration file can be loaded uing the `-c` command line option.

The IoTSuite configuration file format resembles an INI file format, divided into various sections with configuration keys, like so:

```ini
[SANDBOX]
Username = root
Password = toor
ExpTimeout = 300
LoginPrompt = "iotsuite login: "
QMP = no
IpAddr = 192.168.0.3
MacAddr = 52:54:01:12:34:56
```

At initialization, the configuration file is validated and the following required sections are checked for:

- `GENERAL`, containing general uncategorized settings;
- `STATIC`, containing settings for static analysis;
- `DYNAMIC`, containing settings for dynamnic analysis;
- `HEURISTICS`, containing settings for analysis of the collected data;
- `CNC`, containing configuration settings for the fake
C2 VM;
- `SANDBOX`, containing general configuration settings for the
sandbox VM;
- `NETWORK`, containing configuration settings for the network
environment constructed for the VMs to interact, as well as
configuration settings for the custom file transfer protocol
used by IoTSuite.

If any of these settings are missing, IoTSuite will fail with an error.

Each architecture supported by IoTSuite also has its own section, but these sections are not compulsory. The main purpose of these sections is to allow the user to define specific configurations for a specific architecture, although each architecture having its own section is effectively required as each architecture requires its own directory with the specific VM images.

All configuration settings accepted in `SANDBOX` will be overidden by the ones in these sections. If a sample is compiled for an architecture that does not have a section in the configuration file, IoTSuite will fail with an error.

Another section that will be looked for but is not compulsory is the `[IPTABLES]` section. This contains definitions for user-defined `iptables` rules that will be put in place.

The provided default configuration file in [`configs/iotsuite.conf`](../configs/iotsuite.conf) provides the basic settings for IoTSuite to operate. It also comes with comments explaining the function of each configuration key.

## Invocation

IoTSuite has three main subcommands for running samples: `full`, `static`, and `dynamic`. Each subcommand should be self explanatory; invoking IoTSuite without any subcommand will default to `full`.

### Command-Line Options

The following command-line options work with all main subcommands:

- `-c`, `--config` - Specify a configuration file to use for this particular invocation.
- `-v`, `--verbose` - Output more information about the running of IoTSuite.
- `-q`, `--quiet` - Silence informational output, only output on errors and warnings.
- `-x`, `--verify` - Verify that the configuration is valid and works for the given sample and subcommand.
- `-d`, `--dry-run` - Run the entire subcommand without actually starting up the virtual machines or performing any sort of analysis.

### Other Subcommands

The `qemu` subcommand starts up the QEMU virtual machine and allows the user to directly interact with it. The architecture is specified with the `-a` or `--arch` command line option.

Currently not implemented, but it will be.
