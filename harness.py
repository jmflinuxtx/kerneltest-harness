#!/usr/bin/env python

import os
import string
import time
import thread

import fedmsg
import fedmsg.config
import fedmsg.meta

import libvirt

def domainmap(buildrel):
    rawhide = "fc21"
    if buildrel == rawhide:
        domain = "Rawhide"
    else:
        domain = buildrel.replace("fc", "Fedora") + "_"
    return domain

def writelatest(domain, kernel):
    domfilename = domain.replace("_", "")
    domfile = open('/data/latest/%s' %(domfilename), 'w')
    domfile.write(kernel)
    domfile.close()

def launchdomain(domain):
    conn = libvirt.open(None)
    dom = conn.lookupByName(domain)
    if "Rawhide" in domain:
        dom.reboot()
    while True:
        domstate = dom.info()[0]
        if domstate == 5:
           break
        time.sleep(30)
    dom.create()
    print "Domain %s started" % (domain)
 
if __name__ == '__main__':
    pidfile = open('/var/run/harness.pid', 'w')
    pid = str(os.getpid())
    pidfile.write(pid)
    pidfile.close()
    config = fedmsg.config.load_config([], None)
    config['mute'] = True
    config['timeout'] = 0
    fedmsg.meta.make_processors(**config)

    for name, endpoint, topic, msg in fedmsg.tail_messages(**config):
        if "buildsys.build.state.change" in topic:
            matchedmsg = fedmsg.meta.msg2repr(msg, **config)
            if "completed" in matchedmsg:
                if "kernel" in matchedmsg:
                    objectmsg = fedmsg.meta.msg2subtitle(msg, legacy=False, **config)
                    package = string.split(objectmsg, ' ')
                    fcrelease = string.split(package[1], '.')
                    domain = domainmap(fcrelease[-1])
                    logfile = open('/var/log/harness.log', 'a')
                    logfile.write('Testing ' + package + '\n')
                    logfile.close()

                    dom32 = domain + '32'
                    dom64 = domain + '64'
                    print "starting domain %s" % (dom32)
                    thread.start_new(launchdomain, (dom32,))
                    print "starting domain %s" % (dom64)
                    thread.start_new(launchdomain, (dom64,))
