#!/bin/bash

set -e
    
bridge_name="br0"
ip_addr="192.168.0.1/24"

setup() {
    echo "[*] Setting up network bridge with name '$bridge_name'"
    ip link add "$bridge_name" type bridge
    ip link set "$bridge_name" up

    echo "[*] Assigning IP address $ip_addr to bridge '$bridge_name'"
    ip addr add "$ip_addr" brd + dev "$bridge_name"

    echo "[*] Starting dhcpd"
    dhcpd
}

teardown() {
    echo "[*] Killing dhcpd"
    pkill dhcpd

    echo "[*] Disabling and removing bridge '$bridge_name'"
    ip link set "$bridge_name" down
    ip link delete "$bridge_name" type bridge
}

fail() {
    echo "ERROR: $1"
    exit 1
}

[[ $(id -u) == 0 ]] || fail "not run as root"

if [[ $1 == "-s" ]]; then
    setup
elif [[ $1 == "-x" ]]; then
    teardown
else
    fail "unknown argument '$1'"
fi

