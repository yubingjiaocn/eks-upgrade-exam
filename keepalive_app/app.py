from flask import Flask
from kubernetes import client, config
import json
import os

app = Flask(__name__)

config.load_incluster_config()
#config.load_kube_config()

def getInfo():
    temp_dict={}
    temp_dict["candidate"] = getCandidate()
    temp_dict["version"] = getVersion()
    temp_dict["nodes"] = getNodes()
    return json.dumps(temp_dict)

def getCandidate():
    name = os.getenv('CANDIDATE_NAME', default = 'Anonymous')
    return name

def getVersion():
    temp_dict={}
    versionAPI = client.VersionApi()
    version = versionAPI.get_code()
    temp_dict["minor"] = version.minor
    temp_dict["gitVersion"] = version.git_version
    return temp_dict

def getNodes():
    temp_dict={}
    temp_list=[]
    coreAPI = client.CoreV1Api()
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

@app.route('/')
def default():
    return getInfo()

if __name__ == "__main__":
    app.run()