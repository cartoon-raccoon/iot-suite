#!/bin/bash

VM_FOLDER="vms"

if [[ $(basename $(pwd)) != "iot-suite" ]]; then
    echo "ERROR: run from project root"
    exit 1
fi

cd $VM_FOLDER/cnc/

qemu-system-x86_64 \
    -drive file=rootfs.qcow2,format=qcow2 \
    -enable-kvm \
    -m 2G \
    -smp 2 \
    -nic tap,model=virtio-net-pci,helper=/usr/lib/qemu/qemu-bridge-helper,mac=52:54:02:12:34:56