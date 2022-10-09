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

    result["Unreachable_Count"] = int(item["Unreachable_Count"])

    # Check if PDB is configurated
    if item["PDB"] > 0:
        result["PDB_Set"] = True
    else:
        result["PDB_Set"] = False

    # Check if Readiness Gate on Pod is set
    if item["ReadinessGate_Pod"]:
        result["ReadinessGate_Pod"] = True
    else:
        result["ReadinessGate_Pod"] = False

    # Check if Readiness Gate on Pod is set
    if item["preStopHook"]:
        result["preStopHook"] = True
    else:
        result["preStopHook"] = False

    # Check if auto inject Readiness Gate on Namespace is set
    if item["ReadinessGate_NS"]:
        result["ReadinessGate_NS"] = True
    else:
        result["ReadinessGate_NS"] = False

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
        result_str += "Now let's check some extra configuration. \n"

        # Check PDB
        if result["PDB_Set"]:
            result_str += "* PodDisruptionBudget is set.\n"
        else:
            result_str += "* PodDisruptionBudget is not set\n"

        # Check Readiness Gate

        if result["ReadinessGate_NS"]:
            if result["ReadinessGate_Pod"]:
                result_str += "* Readiness Gate is set on Pod and Namespace.\n"
            else:
                result_str += "* Readiness Gate is set on Namespace but not on Pod. Actually it's not working...\n"
        else:
            result_str += "* Readiness Gate is not set.\n"

        # Check pre-stop hook

        if result["preStopHook"]:
            result_str += "* Pre-stop hook for pod is set.\n"
        else:
            result_str += "* Pre-stop hook for pod is not set.\n"

    else:
        result_str += "Something went wrong. Check the output and feel free to try again. \n"
    return result_str

def lambda_handler(event, context):
    timestamp = int(time.time())
    req = json.loads(event['body'])

    awsaccountid = req['AWSAccountID']
    url = "http://" + req['URL'] + "/"

    query = table.get_item(Key={'AWSAccountID': str(awsaccountid)})['Item']

    print(awsaccountid + "has submitted on " + str(timestamp))

    result = judge(query, url)

    print(json.dumps(result))

    table.update_item(Key={'AWSAccountID': awsaccountid},
                      UpdateExpression='SET Submitted = :val1, Passed = :val2, Submitted_Time = :val3',
                      ExpressionAttributeValues={':val1': True, ':val2': result["Final"], ':val3': timestamp})

    result_str = generate_output(query['Name'], result)

    print(result_str)

    return {
        "body": result_str,
        "statusCode": 200
    }
