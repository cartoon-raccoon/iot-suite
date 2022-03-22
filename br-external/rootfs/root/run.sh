#!/bin/sh

#!!!! DO NOT RUN THIS ON THE HOST MACHINE

setup() {
    mkdir /root/fakeroot

    cp -pr /usr /root/fakeroot/usr/
    cp -pr /bin /root/fakeroot/bin/
    cp -pr /etc /root/fakeroot/etc/
    cp -pr /opt /root/fakeroot/opt/
    cp -pr /tmp /root/fakeroot/tmp/
    cp -pr /var /root/fakeroot/var/

    mount --bind /root/fakeroot/proc /proc
    mount --bind /root/fakeroot/sys  /sys
    mount --bind /root/fakeroot/dev  /dev

    cp -p /root/analyse.py /root/fakeroot/analyse.py
}

run() {
    inetsim &
    dumpcap -a duration:60 -w $FILE.pcapng &
    inotifywatch /root/fakeroot &
    # runs strace, ltrace
    chroot /root/fakeroot /root/analyse.py # args
}

cleanup() {
    pkill inetsim

    rm -rf /root/fakeroot
}