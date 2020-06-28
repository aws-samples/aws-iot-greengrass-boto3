# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import argparse
import json
import logging
import os
import random
import sys
import time
import uuid

from AWSIoTPythonSDK.core.greengrass.discovery.providers import DiscoveryInfoProvider
from AWSIoTPythonSDK.core.protocol.connection.cores import ProgressiveBackOffCore
from AWSIoTPythonSDK.exception.AWSIoTExceptions import DiscoveryInvalidRequestException
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

coffee_consumption_stats = {}


def get_coffee_consumption_stats(previous_state):
    if previous_state == None:
        previous_state = {}
        previous_state["total_cups"] = 0
        previous_state["total_beans_usage"] = 0

    next_state = previous_state

    if random.random() > 0.7:
        next_state["total_cups"] = previous_state["total_cups"] + 1
        next_state["total_beans_usage"] = previous_state[
            "total_beans_usage"
        ] + random.randint(10, 20)
    return next_state


# General message notification callback
def customOnMessage(message):
    log.info("Received message on topic %s: %s\n" % (message.topic, message.payload))


MAX_DISCOVERY_RETRIES = 1
GROUP_CA_PATH = "./groupCA/"
DEFAULT_TOPIC = "dt/coffeemonitor/machine"

# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument(
    "-e",
    "--endpoint",
    action="store",
    required=True,
    dest="host",
    help="Your AWS IoT custom endpoint",
)
parser.add_argument(
    "-r",
    "--rootCA",
    action="store",
    required=True,
    dest="rootCAPath",
    help="Root CA file path",
)
parser.add_argument(
    "-c", "--cert", action="store", dest="certificatePath", help="Certificate file path"
)
parser.add_argument(
    "-k", "--key", action="store", dest="privateKeyPath", help="Private key file path"
)
parser.add_argument(
    "-n",
    "--thingName",
    action="store",
    dest="thingName",
    default="Coffeemachine",
    help="Targeted thing name",
)
parser.add_argument(
    "-t",
    "--topic",
    action="store",
    dest="topic",
    default=DEFAULT_TOPIC,
    help="Targeted topic",
)
parser.add_argument(
    "-i",
    "--deviceIdList",
    action="store",
    dest="device_id_list",
    help="List of comma separated numeric device ids to include in MQTT messages",
)

args = parser.parse_args()
host = args.host
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath
clientId = args.thingName
thingName = args.thingName
topic = args.topic
device_id_list = args.device_id_list


if not args.device_id_list:
    parser.error("No Device ID list found")
    exit(3)


if not args.certificatePath or not args.privateKeyPath:
    parser.error(
        "Missing credentials for authentication, you must specify --cert and --key args."
    )
    exit(2)

if not os.path.isfile(rootCAPath):
    parser.error("Root CA path does not exist {}".format(rootCAPath))
    exit(3)

if not os.path.isfile(certificatePath):
    parser.error("No certificate found at {}".format(certificatePath))
    exit(3)

if not os.path.isfile(privateKeyPath):
    parser.error("No private key found at {}".format(privateKeyPath))
    exit(3)

# Configure logging
log = logging.getLogger("coffemachine_simulator")
log.setLevel(logging.INFO)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s : %(message)s")
streamHandler.setFormatter(formatter)
log.addHandler(streamHandler)

# Progressive back off core
backOffCore = ProgressiveBackOffCore()


log.info("--- Input parameters --- ")
log.info("AWS IoT Core endpoint : {}".format(host))
log.info("AWS IoT Thing name    : {}".format(thingName))
log.info("Private certificate   : {}".format(privateKeyPath))
log.info("Private key           : {}".format(certificatePath))


log.info("--- Greengrass discovery started ---")

# GGCs
discoveryInfoProvider = DiscoveryInfoProvider()
discoveryInfoProvider.configureEndpoint(host)
discoveryInfoProvider.configureCredentials(rootCAPath, certificatePath, privateKeyPath)
discoveryInfoProvider.configureTimeout(10)  # 10 sec

retryCount = MAX_DISCOVERY_RETRIES
discovered = False
groupCA = None
coreInfo = None
while retryCount != 0:
    try:
        discoveryInfo = discoveryInfoProvider.discover(thingName)
        caList = discoveryInfo.getAllCas()
        coreList = discoveryInfo.getAllCores()

        # We only pick the first ca and core info
        groupId, ca = caList[0]
        coreInfo = coreList[0]
        log.info("Discovered Core Device for Greengrass Group: %s" % (groupId))

        log.info(
            "Core Device connectivity data: {}:{}".format(
                coreInfo.connectivityInfoList[0].host,
                coreInfo.connectivityInfoList[0].port,
            )
        )

        groupCA = GROUP_CA_PATH + groupId + "_CA_" + str(uuid.uuid4()) + ".crt"
        if not os.path.exists(GROUP_CA_PATH):
            os.makedirs(GROUP_CA_PATH)
        groupCAFile = open(groupCA, "w")
        groupCAFile.write(ca)
        groupCAFile.close()

        discovered = True
        log.info("Group CA certificate was stored in {}".format(groupCA))
        break
    except DiscoveryInvalidRequestException as e:
        log.info("Invalid discovery request detected!")
        log.info("Type: %s" % str(type(e)))
        log.info("Error message: %s" % e.message)
        log.info("Stopping...")
        break
    except BaseException as e:
        log.info("Error in discovery!")
        log.info("Type: %s" % str(type(e)))
        retryCount -= 1
        log.info("\n%d/%d retries left\n" % (retryCount, MAX_DISCOVERY_RETRIES))
        log.info("Backing off...\n")
        backOffCore.backOff()

if not discovered:
    log.info(
        "Discovery failed after %d retries. Exiting...\n" % (MAX_DISCOVERY_RETRIES)
    )
    sys.exit(-1)
log.info(
    "--- Greengrass discovery completed, establishing MQTT session to the Greengrass device  ---"
)


# Iterate through all connection options for the core and use the first successful one
myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
myAWSIoTMQTTClient.configureCredentials(groupCA, privateKeyPath, certificatePath)
myAWSIoTMQTTClient.onMessage = customOnMessage

connected = False
for connectivityInfo in coreInfo.connectivityInfoList:
    currentHost = connectivityInfo.host
    currentPort = connectivityInfo.port
    log.info("Trying to connect to core at %s:%d" % (currentHost, currentPort))
    myAWSIoTMQTTClient.configureEndpoint(currentHost, currentPort)
    try:
        myAWSIoTMQTTClient.connect()
        connected = True
        break
    except BaseException as e:
        log.info("Error in connect!")
        log.info("Type: %s" % str(type(e)))

if not connected:
    log.info("Cannot connect to core %s. Exiting..." % coreInfo.coreThingArn)
    sys.exit(-2)

#    myAWSIoTMQTTClient.subscribe(topic, 0, None)

time.sleep(2)

device_ids = device_id_list.split(",")

for machine_id in device_ids:
    coffee_consumption_stats[machine_id] = None

while True:
    for machine_id in device_ids:
        coffee_consumption_stats[machine_id] = get_coffee_consumption_stats(
            coffee_consumption_stats[machine_id]
        )
        payload = {"device_id": machine_id, **coffee_consumption_stats[machine_id]}

        topic_name = topic + "/" + machine_id

        log.info("Publishing to {}: {}".format(topic_name, json.dumps(payload)))
        myAWSIoTMQTTClient.publish(topic_name, json.dumps(payload), 0)
        time.sleep(1)
