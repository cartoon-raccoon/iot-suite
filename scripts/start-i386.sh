#!/bin/sh

VM_FOLDER="vms"

if [[ $(basename $(pwd)) != "iot-suite" ]]; then
    echo "ERROR: run from project root"
    exit 1
fi

cd $VM_FOLDER/i386/

if [[ $1 == "--ssh-only" ]]; then
	EXTRA_ARGS=""
else
	EXTRA_ARGS="-serial mon:stdio"
fi

exec qemu-system-i386 \
    -M pc \
    -kernel kernel.img \
    -drive file=rootfs.qcow2,if=virtio,format=qcow2 \
    -append "rootwait quiet root=/dev/vda console=tty1 console=ttyS0" \
    -nic tap,model=virtio,helper=/usr/lib/qemu/qemu-bridge-helper,mac=52:54:01:12:34:56 \
    -nographic ${EXTRA_ARGS}