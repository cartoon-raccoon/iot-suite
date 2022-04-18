#!/bin/bash

set -e


# config
bridge_name="br0"
ip_addr="192.168.0.1/24"
cnc_ip="192.168.0.2"

# set up bridge device with ip, start dhcp, add iptables rules
setup() {
    echo "[*] Setting up network bridge with name '$bridge_name'"
    ip link add "$bridge_name" type bridge
    ip link set "$bridge_name" up

    echo "[*] Assigning IP address $ip_addr to bridge '$bridge_name'"
    ip addr add "$ip_addr" brd + dev "$bridge_name"

    echo "[*] Starting dhcpd"
    dhcpd

    natsetup
}

# teardown all devices, kill dhcpd, remove iptables rules
teardown() {
    echo "[*] Killing dhcpd"
    pkill dhcpd || echo "[!] dhcpd not running"

    echo "[*] Disabling and removing bridge '$bridge_name'"
    ip link set "$bridge_name" down
    ip link delete "$bridge_name" type bridge

    echo "[*] Deleting iptables rules"
    iptables -t nat -D PREROUTING 1
    iptables -t nat -D POSTROUTING 1
}

# restart dhcpd to apply new settings
dhcprestart() {
    echo "[*] Restarting dhcpd"
    pkill dhcpd
    sleep 2

    dhcpd
}

# apply iptables rules
natsetup() {
    echo "[*] Adding iptables rules using bridge '$bridge_name' and CNC IP '$cnc_ip'"
    iptables -t nat \
        -A PREROUTING -i $bridge_name \
        -j DNAT --to-destination $cnc_ip
    iptables -t nat \
        -I POSTROUTING -s $cnc_ip -o $bridge_name \
        -j MASQUERADE
    
    echo "Current iptables rules setup:"
    iptables -t nat -L
}

fail() {
    echo "ERROR: $1"
    exit 1
}

[[ $(id -u) == 0 ]] || fail "not run as root"

case "$1" in
-s)
    setup
    ;;
-x)
    teardown
    ;;
-r)
    dhcprestart
    ;;
-n)
    natsetup
    ;;
?)
    fail "unknown argument '$1'"
    ;;
*)
    fail "no argument given (use -s/-x/-r)"
    ;;
esac


