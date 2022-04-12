#!/bin/sh

VM_FOLDER="vms"

if [[ $(basename $(pwd)) != "iot-suite" ]]; then
    echo "ERROR: run from project root"
    exit 1
fi

cd $VM_FOLDER/mips/

if [ "${1}" = "serial-only" ]; then
    EXTRA_ARGS='-nographic'
else
    EXTRA_ARGS="-serial mon:stdio"
fi

exec qemu-system-mips \
    -M malta -cpu mips32r6-generic \
    -kernel kernel.img \
    -drive file=rootfs.ext2,format=raw \
    -append "rootwait root=/dev/sda quiet" \
    -nic tap,model=pcnet,helper=/usr/lib/qemu/qemu-bridge-helper,mac=52:54:00:12:34:56 \
    -nographic  ${EXTRA_ARGS}

