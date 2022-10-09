from flask import Flask
from kubernetes import client, config
import json
import os

app = Flask(__name__)
if os.getenv('CONFIG', default = 'IN') == 'EXTERNAL':
    config.load_kube_config()
else:
    config.load_incluster_config()


def getInfo():
    temp_dict={}
    temp_dict["candidate"] = getCandidate()
    temp_dict["version"] = getVersion()
    temp_dict["nodes"] = getNodes()
    temp_dict["workloads"] = getWorkloads()
    temp_dict["pdbs"] = getPDBs()
    temp_dict["pods"] = getPods()
    temp_dict["namespaces"] = getNamespaces()
    return json.dumps(temp_dict)

def getCandidate():
    name = os.getenv('CANDIDATE_NAME', default = 'Anonymous')
    return name

def getVersion():
    temp_dict={}

    versionAPI = client.VersionApi()

    #Get cluster version
    version = versionAPI.get_code()
    temp_dict["minor"] = version.minor
    temp_dict["gitVersion"] = version.git_version
    return temp_dict

def getNodes():
    temp_dict={}
    temp_list=[]

    coreAPI = client.CoreV1Api()

    # Get all node info
    client_output = coreAPI.list_node()
    json_data=client.ApiClient().sanitize_for_serialization(client_output)

    #print("JSON_DATA OF KUBERNETES OBJECT:{}".format(json_data))

    if len(json_data["items"]) != 0:
        for node in json_data["items"]:
            temp_dict={
                "node": node["metadata"]["name"],
                "version": node["status"]["nodeInfo"]["kubeletVersion"]
            }
            temp_list.append(temp_dict)

    return temp_list

def getWorkloads():
    temp_dict={}

    appAPI = client.AppsV1Api()

    # Get kube-proxy daemonset
    api_response = appAPI.read_namespaced_daemon_set(name="kube-proxy", namespace="kube-system")
    json_data=client.ApiClient().sanitize_for_serialization(api_response)

    # Read image tag
    temp_dict["kube-proxy"] = json_data["spec"]["template"]["spec"]["containers"][0]["image"]

    return temp_dict

def getPDBs():
    temp_dict={}

    policyAPI = client.PolicyV1Api()

    # Get all PDB info
    client_output = policyAPI.list_namespaced_pod_disruption_budget(namespace='exam')
    json_data=client.ApiClient().sanitize_for_serialization(client_output)

    count = 0
    if len(json_data["items"]) != 0:
        for pdb in json_data["items"]:
            # Directly return a proper configurated PDB count
            if pdb["spec"]["selector"]["matchLabels"]["app"] == "exam-keepalive": count += 1

    #print("JSON_DATA OF PDB:{}".format(json_data))
    temp_dict["count"] = count
    return temp_dict

def getPods():
    temp_dict={}

    coreAPI = client.CoreV1Api()

    # Only get related pod
    client_output = coreAPI.list_namespaced_pod(namespace="exam", label_selector='app=exam-keepalive')
    json_data=client.ApiClient().sanitize_for_serialization(client_output)

    readinessGate = False
    preStopHook = False

    if len(json_data["items"]) != 0:
        for pod in json_data["items"]:
            # Find if readinessGate exists
            if "readinessGates" in pod["spec"]:
                # Check if readinessGate is created by ALB
                for gates in pod["spec"]["readinessGates"]:
                    if "target-health.elbv2.k8s.aws" in gates["conditionType"]:
                        readinessGate = True

            if "lifecycle" in pod["spec"]["containers"][0]:
                # Check if pre-stop hook is configurated
                    if "preStop" in pod["spec"]["containers"][0]["lifecycle"]:
                        preStopHook = True

    #print("JSON_DATA OF KUBERNETES OBJECT:{}".format(json_data))

    temp_dict["readinessGate"] = readinessGate
    temp_dict["preStopHook"] = preStopHook
    return temp_dict

def getNamespaces():
    temp_dict={}
    coreAPI = client.CoreV1Api()

    # Get exam namespace
    client_output = coreAPI.list_namespace(field_selector="metadata.name=exam")
    json_data=client.ApiClient().sanitize_for_serialization(client_output)

    readinessGate = False
    if len(json_data["items"]) != 0:
        for ns in json_data["items"]:
            # Find if readinessGate exists
            if "elbv2.k8s.aws/pod-readiness-gate-inject" in ns["metadata"]["labels"]:
                readinessGate = True

    temp_dict["readinessGate"] = readinessGate

    return temp_dict


@app.route('/')
def default():
    return getInfo()

if __name__ == "__main__":
    app.run()