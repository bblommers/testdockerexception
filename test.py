import json
import uuid
import boto3
import os
from moto.awslambda import mock_lambda
from moto.sts import mock_sts
from moto.iam import mock_iam


@mock_sts
@mock_iam
@mock_lambda
def test_invoke():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-2"

    CLIENT_IAM = boto3.client("iam",
                              )
    CLIENT_LAMBDA = boto3.client("lambda"
                                 )

    # Generate a random function name (with prefix 'pytest.')
    function_name = "pytest_" + str(uuid.uuid4())

    # Create a role that allows us to manage Lambda (prefixed similarly)
    role_name = "pytest." + str(uuid.uuid4())

    # Policy Document for Trust Relationship for Lambda Basic Execution Role
    policy_trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    # Role creation
    response = CLIENT_IAM.create_role(
        RoleName=role_name, AssumeRolePolicyDocument=json.dumps(policy_trust)
    )

    role_arn = response["Role"]["Arn"]

    # Attach AdministratorAccess policy to the created role
    _policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
    CLIENT_IAM.attach_role_policy(RoleName=role_name, PolicyArn=_policy_arn)

    script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
    rel_path = "serverless_helloworld.zip"
    abs_file_path = os.path.join(script_dir, rel_path)

    CLIENT_LAMBDA.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=role_arn,
        Handler="serverless_helloworld.lambda_handler",
        Code={"ZipFile": open(abs_file_path, "rb").read(),},
    )

    payload = {"param": "Hello world"}
    payload_bytes = json.dumps(payload).encode("utf-8")

    _kwargs = {
        "FunctionName": function_name,
        "InvocationType": 'RequestResponse',
        "Payload": payload_bytes,
    }

    response = CLIENT_LAMBDA.invoke(**_kwargs, Qualifier="$LATEST")
    response_body = response["Payload"].read()
    print("Response Body:")
    print(response_body)

   
    assert json.loads(response_body) == payload["param"]
