#!/bin/sh

VM_FOLDER="vms"

if [[ $(basename $(pwd)) != "iot-suite" ]]; then
    echo "ERROR: run from project root"
    exit 1
fi

cd $VM_FOLDER/aarch64/

if [ "${1}" = "serial-only" ]; then
    EXTRA_ARGS='-nographic -serial mon:stdio'
else
    EXTRA_ARGS=''
fi

exec qemu-system-aarch64 \
    -M virt -cpu cortex-a53 -smp 1 -kernel kernel.img \
    -append "rootwait root=/dev/vda console=ttyAMA0 quiet" \
    -nic tap,model=pcnet,helper=/usr/lib/qemu/qemu-bridge-helper,mac=52:54:04:12:34:56 \
    -serial mon:stdio -nographic \
    -drive file=rootfs.qcow2,if=none,format=qcow2,id=hd0 \
    -device virtio-blk-device,drive=hd0  ${EXTRA_ARGS}
