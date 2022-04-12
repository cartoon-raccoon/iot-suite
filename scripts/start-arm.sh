#!/bin/sh

VM_FOLDER="vms"

if [[ $(basename $(pwd)) != "iot-suite" ]]; then
    echo "ERROR: run from project root"
    exit 1
fi

cd $VM_FOLDER/arm/

if [[ $1 == "--ssh-only" ]]; then
	EXTRA_ARGS=""
else
	EXTRA_ARGS="-serial mon:stdio"
fi

if ! [ -f /tmp/guest.in ] || [ -f /tmp/guest.out ]; then
	mkfifo /tmp/guest.in /tmp/guest.out
fi

exec qemu-system-arm \
	-M versatilepb \
	-kernel kernel.img \
	-dtb versatile-pb.dtb \
	-drive file=rootfs.ext2,if=scsi,format=raw \
	-append "rootwait quiet root=/dev/sda console=ttyAMA0,115200" \
	-nic tap,model=rtl8139,helper=/usr/lib/qemu/qemu-bridge-helper,mac=52:54:01:12:34:56 \
	-nographic ${EXTRA_ARGS}

	#-net hostfwd=tcp::5555-:22,hostfwd=tcp::5554-:21 \
