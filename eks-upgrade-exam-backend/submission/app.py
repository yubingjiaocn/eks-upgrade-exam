import os
import boto3
import json
import requests
import time
from requests.adapters import HTTPAdapter
from boto3.dynamodb.conditions import Key

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

session = requests.Session()
session.mount('http://', HTTPAdapter(max_retries=3))

def judge(item, url):
    passed = True
    result = {}

    # Check cluster version
    if item["Cluster_Ver"] == 22:
        result["Cluster_Update"] = True
    else:
        result["Cluster_Update"] = False
        passed = False   

    # Check node version
    result["Node_All_Update"] = True
    for node in item["Nodes_Ver"]:
        if node < 22: 
            result["Node_All_Update"] = False
            passed = False

    # Check kube-proxy version
    if item["Kube_Proxy_Ver"] == 22:
        result["Kube_Proxy_Update"] = True
    else:
        result["Kube_Proxy_Update"] = False
        passed = False

    # Check if test application is deployed
    try:
        access_check = session.get(url, timeout=(0.3, 1)) 
        if access_check.ok:
            if access_check.text == "{'test': 'OK'}":
                result["Access_Check"] = True
            else:
                result["Access_Check"] = False
                passed = False
    except requests.exceptions.RequestException:
            result["Access_Check"] = False
            passed = False 

    result["Unreachable_Count"] = item["Unreachable_Count"]
    if item["Unreachable_Count"] > 0: 
        passed = False

    result["Final"] = passed
    return result

def generate_output(name, result):
    result_str = "Candidate: " + name + "\n"

    # Check cluster version
    if result["Cluster_Update"]:
        result_str += "* Cluster control plane is updated\n"
    else:
        result_str += "* Cluster control plane is not updated\n" 

    # Check node version
    if result["Node_All_Update"]:
        result_str += "* All worker nodes are updated\n"
    else:
        result_str += "* Not all worker nodes are updated\n" 

    # Check kube-proxy version
    if result["Kube_Proxy_Update"]:
        result_str += "* Kube-proxy is updated\n"
    else:
        result_str += "* Kube-proxy is not updated\n"

    # Check if test application is deployed

    if result["Access_Check"]:
        result_str += "* Test application is deployed\n"
    else:
        result_str += "* Test application is not deployed\n"

    result_str += "* Unreachable count: " + str(result["Unreachable_Count"]) + "\n"

    if result["Final"]:
        result_str += "Congratulations! You have passed the exam. \n"
    else: 
        result_str += "Something went wrong. Check the output and feel free to try again. \n"
    return result_str

def lambda_handler(event, context):
    req = json.loads(event['body'])

    awsaccountid = req['AWSAccountID']

    query = table.get_item(Key={'AWSAccountID': str(awsaccountid)})['Item']

    result = judge(query, req['URL'])

    if result["Final"]:
        timestamp = int(time.time())
        table.update_item(Key={'AWSAccountID': awsaccountid},
                      UpdateExpression='SET Submitted = :val1, Submitted_Time = :val2',
                      ExpressionAttributeValues={':val1': True, ':val2': timestamp})

    result_str = generate_output(query['Name'], result)
    
    return {
        "body": result_str,
        "statusCode": 200
    }
