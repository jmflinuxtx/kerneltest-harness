# Licensed under the terms of the GNU GPL License version 2

import logging
import time
import _thread

import libvirt


_log = logging.getLogger(__name__)

RAWHIDE = "fc31"


def launchdomain(domain):
    conn = libvirt.open(None)
    dom = conn.lookupByName(domain)
    if "Rawhide" in domain:
        dom.reboot()
    else:
        while True:
            domstate = dom.info()[0]
            if domstate == 5:
                break
            time.sleep(30)
        dom.create()
    _log.info("Domain %s started", domain)


def callback(message):
    """
    A fedora-messaging callback invoked when messages arrive.

    This can be run with::

        $ fedora-messaging consume --callback=kerneltest.harness:callback

    This callback is meant to be run on messages from Koji. The topic should be
    "org.fedoraproject.*.buildsys.build.state.change".

    Args:
        message (fedora_messaging.api.Message): The AMQP message.
    """

    # Koji messages are *INSANE*, this is completed undocumented and when it
    # breaks it's not my fault. There's a "new" field, and if it's 0 it
    # apparently means the build started, and if it's 1 that means the build
    # completed. We're only interested in completed kernel builds. I am truly
    # sorry.
    if message.body.get("new", 0) != 1 or message.body.get("name") != "kernel":
        return

    try:
        release = message.body["release"].split(".")[-1]
        domain = (
            "Rawhide" if release == RAWHIDE else release.replace("fc", "Fedora") + "_"
        )
    except KeyError:
        _log.error("Koji message %s did not have a 'release' key", message.id)
        return

    package = "{}-{}-{}".format(
        message.body["name"], message.body["version"], message.body["release"]
    )
    with open("/data/latest/{}".format(domain.replace("_", "")), "w") as domfile:
        domfile.write(package)

    _log.info("Testing %s", package)
    for dom in [domain + "32", domain + "64"]:
        _log.info("Starting domain %s", dom)
        _thread.start_new(launchdomain, (dom,))
