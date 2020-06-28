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


import copy
import json
import os
import time


def format_apicall_result(title, payload, remove_keys):
    payload_after_removal = copy.deepcopy(payload)
    for key in remove_keys:
        if key in payload_after_removal:
            payload_after_removal.pop(key, None)
    return 'Output of API call "{}":{}'.format(
        title, json.dumps(payload_after_removal, indent=2, sort_keys=True)
    )


def mkdir(directory):
    try:
        os.mkdir(directory)
    except FileExistsError:
        return


def save_jsondump_to_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def save_string_to_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(data)
        f.close()


def read_string_from_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = f.read()
        f.close()
        return data


def lookup(
    input_json, matching_attribute_name, matching_attribute_value, result_attribute
):
    for item in input_json:
        if (item[matching_attribute_name]) == matching_attribute_value:
            return item[result_attribute]
    return None


# Check for role existence.


def role_exists(iam, role_name):
    try:
        iam.get_role(RoleName=role_name)
    except iam.exceptions.NoSuchEntityException:
        return False
    else:
        return True


def role_arn_byname(iam, role_name):
    response = iam.get_role(RoleName=role_name)
    return response["Role"]["Arn"]


def create_greengrass_group_role(iam, GroupRoleName, GroupRolePolicy):
    if role_exists(iam, GroupRoleName):
        return role_arn_byname(iam, GroupRoleName)

    # Define the assume role policy
    grouprole_assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": ["lambda.amazonaws.com", "greengrass.amazonaws.com"]
                },
                "Action": "sts:AssumeRole",
            }
        ],
    }

    # Create role
    response = iam.create_role(
        RoleName=GroupRoleName,
        AssumeRolePolicyDocument=json.dumps(grouprole_assume_role_policy),
    )

    # Attach policy to the role
    iam.put_role_policy(
        RoleName=GroupRoleName,
        PolicyName="inline_policy_1",
        PolicyDocument=json.dumps(GroupRolePolicy),
    )

    return response["Role"]["Arn"]


def create_lambda_function(
    FunctionName, RoleName, CodeZipFilePath, FunctionAliasName, iam, log, lambda_client
):
    # Define role for Lambda Function. This is only for demonstration and not to be used in production environment.

    if not role_exists(iam, RoleName):
        response = iam.create_role(
            RoleName=RoleName,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )
        lambda_role_arn = response["Role"]["Arn"]
        log.info("Role created, wait 15 seconds till the policies get effective")
        time.sleep(15)

    else:
        log.info("Reusing existing role")
        lambda_role_arn = role_arn_byname(iam, RoleName)

    log.info(
        "Role with ARN {} will be used when creating an AWS Lambda function".format(
            lambda_role_arn
        )
    )
    # Create a new AWS Lambda function

    lambda_function = lambda_client.create_function(
        FunctionName=FunctionName,
        Runtime="python3.7",
        Role=lambda_role_arn,
        Handler="lambda.function_handler",
        Code={"ZipFile": open(CodeZipFilePath, "rb").read()},
        Timeout=30,
        MemorySize=128,
        Description="Sample Lambda function",
        Publish=True,
    )

    lambda_function_arn = lambda_function["FunctionArn"]

    log.info("AWS Lambda function created with ARN {}".format(lambda_function_arn))

    # Create aliases for AWS Lambda functions (3c)
    lambda_client.create_alias(
        FunctionName=FunctionName,
        Name=FunctionAliasName,
        FunctionVersion="1",
        Description="Alias for Greengrass deployment",
    )

    lambda_function_arn_fullqualified = lambda_function_arn + ":" + FunctionAliasName

    return lambda_function_arn_fullqualified
