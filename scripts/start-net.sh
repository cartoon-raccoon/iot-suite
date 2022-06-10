#!/bin/bash

set -e

declare -Ar ports=(21 22 23 25 443 990 1 995 37 7 9 6667 13 2222 80 2224)

# config
bridge_name="br0"
ip_addr="192.168.0.1"
netmask="24"
cnc_ip="192.168.0.2"

# set up bridge device with ip, start dhcp, add iptables rules
setup() {
    echo "[*] Setting up network bridge with name '$bridge_name'"
    ip link add "$bridge_name" type bridge
    ip link set "$bridge_name" up

    echo "[*] Assigning IP address $ip_addr to bridge '$bridge_name'"
    ip addr add "$ip_addr/$netmask" brd + dev "$bridge_name"

    echo "[*] Starting dhcpd"
    dhcpd

    # natsetup
}

# teardown all devices, kill dhcpd, remove iptables rules
teardown() {
    echo "[*] Killing dhcpd"
    pkill dhcpd || echo "[!] dhcpd not running"

    echo "[*] Disabling and removing bridge '$bridge_name'"
    ip link set "$bridge_name" down
    ip link delete "$bridge_name" type bridge

    echo "[*] Deleting iptables rules"
    iptables -t nat -F
    iptables -t mangle -F
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

    for port in "${ports[@]}"; do
        echo "Adding iptables for port $port"
        iptables -t nat -A PREROUTING -i $bridge_name -p tcp --dport $port \
            -s 192.168.0.3 \
            -j DNAT --to-destination $cnc_ip:$port
    done

    iptables -t nat \
        -I POSTROUTING -o $bridge_name -j MASQUERADE
    
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


