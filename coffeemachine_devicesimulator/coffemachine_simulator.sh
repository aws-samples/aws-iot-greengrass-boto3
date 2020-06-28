#!/bin/sh
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


# Set a device name
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 DEVICE_NAME DEVICE_CERT_PATH DEVICE_KEY_PATH DEVICE_ID_LIST"
    echo "Example: $0 CoffeeMachine1 certs/CoffeeMachine_1.pem certs/CoffeeMachine_1.key 1"
    exit 1
fi


DEVICE_NAME=$1
ROOT_CERT_PATH=certs/AmazonRootCA1.pem 
DEVICE_CERT_PATH=$2
DEVICE_KEY_PATH=$3

DEVICE_ID_LIST=$4

# Identify an AWS IoT endpoint 
AWS_IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS | jq -r .endpointAddress) 

python coffemachine_simulator.py   -e $AWS_IOT_ENDPOINT \
                                    -r $ROOT_CERT_PATH   \
                                    -c $DEVICE_CERT_PATH \
                                    -k $DEVICE_KEY_PATH  \
                                    -n $DEVICE_NAME      \
                                    -i $DEVICE_ID_LIST
