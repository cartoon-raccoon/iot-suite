#!/bin/sh

VM_FOLDER="vms"

if [[ $(basename $(pwd)) != "iot-suite" ]]; then
    echo "ERROR: run from project root"
    exit 1
fi

cd $VM_FOLDER/mipsel/

if [ "${1}" = "serial-only" ]; then
    EXTRA_ARGS='-nographic'
else
    EXTRA_ARGS=''
fi

exec qemu-system-mipsel \
    -M malta -cpu mips32r6-generic \
    -kernel kernel.img \
    -drive file=rootfs.qcow2,format=qcow2 \
    -append "rootwait root=/dev/sda quiet" \
    -nic tap,model=pcnet,helper=/usr/lib/qemu/qemu-bridge-helper,mac=52:54:00:12:34:56 \
    -serial mon:stdio \
    -nographic  ${EXTRA_ARGS}


# -net user,id=eth0,hostfwd=tcp::7555-:22,hostfwd=tcp::7554-:21,restrict=y \