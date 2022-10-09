import os
import time
import boto3
import json
import requests
from requests.adapters import HTTPAdapter
from boto3.dynamodb.conditions import Key, Attr

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

session = requests.Session()
session.mount('http://', HTTPAdapter(max_retries=3))

def scrape(item):
    print("Working on: " + item["AWSAccountID"])
    timestamp = int(time.time())
    url = "http://" + item["IngressURL"] + "/"
    print("URL: "+ url)
    unreachable_count = item["Unreachable_Count"]

    # Scrap from cluster's exam application
    try:
        resp = session.get(url, timeout=(0.3, 1))
        if resp.ok:
            payload = json.loads(resp.text)
            print(json.dumps(payload))
            # Cut cluster version ("22+" -> "22")
            cluster_ver = int(payload["version"]["minor"][0:2])

            # Cut node version ("v1.22.12-eks-ba74326" -> "22")
            nodes_ver = []
            for node in payload["nodes"]:
                nodes_ver.append(int(node["version"][3:5]))

            # Cut image tag ("602401143452.dkr.ecr.ap-southeast-1.amazonaws.com/eks/kube-proxy:v1.22.11-eksbuild.2" -> "v1.22.11-eksbuild.2" -> "22")
            # TBD: I hardcoded kube-proxy, but can add something more
            kube_proxy_ver = int(payload["workloads"]["kube-proxy"].split(":")[1][3:5])

            # Get PDB
            pdb = int(payload["pdbs"]["count"])

            # Get pod readiness gate
            readinessGate_Pod = payload["pods"]["readinessGate"]

            # Get pod pre-stop hook
            preStopHook = payload["pods"]["preStopHook"]

            # Get ns readiness gate
            readinessGate_NS = payload["namespaces"]["readinessGate"]

            # Write to DynamoDB
            table.update_item(Key={'AWSAccountID': item["AWSAccountID"]},
                      UpdateExpression='SET Last_Access = :val1, Unreachable_Count = :val2, Cluster_Ver = :val3, Nodes_Ver = :val4, Kube_Proxy_Ver = :val5, PDB = :val6, ReadinessGate_Pod = :val7, preStopHook = :val8, ReadinessGate_NS = :val9',
                      ExpressionAttributeValues={':val1': timestamp, ':val2': unreachable_count, ':val3': cluster_ver, ':val4': nodes_ver, ':val5': kube_proxy_ver, ':val6': pdb, ':val7': readinessGate_Pod, ':val8': preStopHook, ':val9': readinessGate_NS})

    # When exam app is unreachable
    except requests.exceptions.RequestException:
        if timestamp - item["Start_Time"] < 120:
            print("Candidate " + item["AWSAccountID"] + " is in grace period")
        else:
            print("Unable to connect to candidate " + item["AWSAccountID"] + " application")
            unreachable_count = unreachable_count + 1
            table.update_item(Key={'AWSAccountID': item["AWSAccountID"]},
                      UpdateExpression='SET Last_Access = :val1, Unreachable_Count = :val2',
                      ExpressionAttributeValues={':val1': timestamp, ':val2': unreachable_count})

    return

def lambda_handler(event, context):
    response = table.scan()
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    count = len(data)
    print(f"Current candidates: {count}")

    for item in data:
        scrape(item)

    return {
        "statusCode": 200
    }
