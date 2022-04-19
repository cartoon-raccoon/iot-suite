#!/bin/bash

VM_FOLDER="vms"

if [[ "$1" == "-h" ]]; then
    NET_ARGS="-nic tap,model=virtio-net-pci,helper=/usr/lib/qemu/qemu-bridge-helper,mac=52:54:02:12:34:56"

    echo "[*] Starting fakec2 on host-only network"
    echo "NOTE: There is no internet connection in this config"
elif [[ "$1" == "-i" ]]; then
    NET_ARGS=""

    echo "[*] Starting fakec2 with internet connection"
    echo "NOTE: The fakec2 is unable to communicate with the test VMs in this config"
else
    echo "[!] No valid option given, exiting"
    exit 1
fi

if [[ $(basename $(pwd)) != "iot-suite" ]]; then
    echo "ERROR: run from project root"
    exit 1
fi

cd $VM_FOLDER/cnc/

exec qemu-system-x86_64 \
    -drive file=rootfs.qcow2,format=qcow2 \
    -enable-kvm \
    -serial mon:stdio -nographic \
    -m 2G \
    -smp 2 ${NET_ARGS}