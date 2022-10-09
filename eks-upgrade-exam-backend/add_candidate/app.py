import time
import boto3
import os
import json
from boto3.dynamodb.conditions import Key

tablename = os.environ.get('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

def lambda_handler(event, context):
    #print(json.dumps(event, indent=2))
    req = json.loads(event['body'])
    awsaccountid = req['AWSAccountID']
    name = req['Name']
    ingressurl = req['IngressURL']
    start_timestamp = int(time.time())

    response = table.query(KeyConditionExpression=Key('AWSAccountID').eq(str(awsaccountid)))
    print(response)
    if len(response['Items']) == 0:
        item = {
            'AWSAccountID': awsaccountid,
            'Name': name,
            'IngressURL': ingressurl,
            'Start_Time': start_timestamp,
            'Last_Access': start_timestamp,
            'Unreachable_Count': 0,
            'Passed': False
        }

        table.put_item(Item=item)
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({'message': 'This AWS Account ID already registered. Please contact instructor for assistance. '})
        }

    return {
        "statusCode": 200
    }
