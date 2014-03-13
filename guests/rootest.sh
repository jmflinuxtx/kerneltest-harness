#!/bin/bash
#
# Licensed under the terms of the GNU GPL License version 2

FedoraRelease=Fedora20
currentkernel=kernel-`uname -r`
if [ ! -f /data/latest/$FedoraRelease ]; then
    mount /data
fi
latestkernel=`cat /data/latest/$FedoraRelease`
kojidir=/home/kerneltest/koji/
kerneltestdir=/home/kerneltest/kernel-tests/
trinitydir=/home/kerneltest/trinity/

#Make sure we are on the latest kernel, install if not
if [ "$currentkernel" != "$latestkernel.x86_64" ]
then
    cd $kojidir
    rm *.rpm
    koji download-build --arch=x86_64 $latestkernel
    rm *debug*.rpm
    yum -y update *.rpm
    reboot
fi

#We are on the latest kernel, run some tests
cd $kerneltestdir

#Regression Test as root
./runtests.sh
if [ "$result" != "0" ]
then
    echo "Regression Test Suite fail for kernel $currentkernel" >> /data/logs/$FedoraRelease
fi
/usr/sbin/shutdown now -h
