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

import json
import logging
import sys
import threading

import boto3

from flask import Flask, render_template

############ Begin of configuration ############

# Function name for logging
FUNCTION_NAME = "CoffeMachineMonitor"
#  Flask web server will be listening on this port
HTTP_PORT = "8081"
# Topic for communication to the AWS Cloud, must be configured in  "Subscriptions" part of AWS Greeengrass group
TOPIC_CLOUD_ANALYTICS = "dt/coffeemonitor/machines"

# Global variables
data_per_device = {}

############ End of configuration ############

# Create an instance of a low-level client representing AWS IoT Data Plane
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iot-data.html
cloud_iot_client = boto3.client("iot-data")


def publish_message_cloud(topic, message):
    """ Publishes message to the AWS IoT Greengrass Core
    Parameters
    ----------
    topic : str
        MQTT topic

    message : str
        JSON formatted message
    """
    cloud_iot_client.publish(topic=topic, qos=0, payload=json.dumps(message))


def function_handler(event, context):
    """This function will be called when the AWS Lambda receives an MQTT
    message."""
    global data_per_device
    logger.info("function_handler received message: {}".format(json.dumps(event)))
    device_name = event["device_id"]
    data_per_device[device_name] = event
    logger.info("Publishing message to cloud : {}".format(data_per_device))
    publish_message_cloud(TOPIC_CLOUD_ANALYTICS, data_per_device)


# Create a Flask application and enable reloading of HTML templates at runtime
app = Flask(FUNCTION_NAME)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Setup logging
logger = logging.getLogger(FUNCTION_NAME)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# A route for main page
@app.route("/")
def index():
    """Returns the /index.html page."""
    global data_per_device
    return render_template("index.html", message="", data_per_device=data_per_device)


# Start Flask application. We are using threading to ensure that Flask application is not blocking
# the invokation of "function_handler" function


def flask_application():
    """Starts a web server in a separte thread."""
    app.run(
        threaded=True, debug=False, use_reloader=False, host="0.0.0.0", port=HTTP_PORT
    )


threading.Thread(target=flask_application).start()
