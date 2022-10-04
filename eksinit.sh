# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
#

#title           eksinit.sh
#description     This script will setup the Cloud9 IDE with the prerequisite packages and code for the EKS workshop.
#author          Imaya Kumar Jagannathan (@ijaganna)
#contributors    Rob Solomon (@rosolom) 
#date            2022-04-18
#version         1.2
#usage           aws s3 cp s3://ee-assets-prod-us-east-1/modules/bd7b369f613f452dacbcea2a5d058d5b/v5/eksinit.sh . && chmod +x eksinit.sh && ./eksinit.sh ; source ~/.bash_profile ; source ~/.bashrc

# MODIFIED BY BINGJIAO YU
# Purpose: Use for eks upgrade exam
#==============================================================================

REPO_PATH = "https://github.com/yubingjiaocn/eks-upgrade-exam.git"
ADD_URL = 


read -p 'Please input your name in full Pinyin. (e.g. Yu Bingjiao) :' CANDIDATE_NAME
echo "export CANDIDATE_NAME=${CANDIDATE_NAME}" | tee -a ~/.bash_profile

####################
##  Tools Install ##
####################

# reset yum history
sudo yum history new

# Install jq (json query)
sudo yum -y -q install jq

# Install yq (yaml query)
echo 'yq() {
  docker run --rm -i -v "${PWD}":/workdir mikefarah/yq "$@"
}' | tee -a ~/.bashrc && source ~/.bashrc

# Install other utils:
#   gettext: a framework to help other GNU packages product multi-language support. Part of GNU Translation Project.
#   bash-completion: supports command name auto-completion for supported commands
#   moreutils: a growing collection of the unix tools that nobody thought to write long ago when unix was young
sudo yum -y install gettext bash-completion moreutils

# Update awscli v1, just in case it's required
pip install --user --upgrade awscli

# Install awscli v2
curl -O "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"
unzip -o awscli-exe-linux-x86_64.zip
sudo ./aws/install
rm awscli-exe-linux-x86_64.zip

# Configure Cloud9 creds
aws cloud9 update-environment  --environment-id $C9_PID --managed-credentials-action DISABLE

# Install kubectl
#  enable desired version by uncommenting the desired version below:
#   kubectl version 1.19
#   curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.19.6/2021-01-05/bin/linux/amd64/kubectl
#   kubectl version 1.20
#   curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.20.4/2021-04-12/bin/linux/amd64/kubectl
#   kubectl v1.21
curl -o kubectl https://s3.us-west-2.amazonaws.com/amazon-eks/1.21.2/2021-07-05/bin/linux/amd64/kubectl
#   kubectl v1.22
#  curl -o kubectl https://s3.us-west-2.amazonaws.com/amazon-eks/1.22.6/2022-03-09/bin/linux/amd64/kubectl

# set kubectl as executable, move to path, populate kubectl bash-completion
chmod +x kubectl && sudo mv kubectl /usr/local/bin/
echo "source <(kubectl completion bash)" >> ~/.bashrc
echo "source <(kubectl completion bash | sed 's/kubectl/k/g')" >> ~/.bashrc

# Install c9 for editing files in cloud9
npm install -g c9

# Install eksctl and move to path
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Install helm
curl -sSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

#####################
##  Set Variables  ##
#####################

# Set AWS region in env and awscli config
AWS_REGION=$(curl --silent http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)
echo "export AWS_REGION=${AWS_REGION}" | tee -a ~/.bash_profile
echo "export AWS_DEFAULT_REGION=${AWS_REGION}" | tee -a ~/.bash_profile

# Set accountID
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
echo "export ACCOUNT_ID=${ACCOUNT_ID}" | tee -a ~/.bash_profile

# Set EKS cluster name
EKS_CLUSTER_NAME=$(aws eks list-clusters --region ${AWS_REGION} --query clusters --output text)
echo "export EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME}" | tee -a ~/.bash_profile
echo "export CLUSTER_NAME=${EKS_CLUSTER_NAME}" | tee -a ~/.bash_profile

# Update kubeconfig and set cluster-related variables if an EKS cluster exists

if [[ "${EKS_CLUSTER_NAME}" != "" ]]
then

# Update kube config
    aws eks update-kubeconfig --name ${EKS_CLUSTER_NAME} --region ${AWS_REGION} 

# Set EKS node group name
    EKS_NODEGROUP=$(aws eks list-nodegroups --cluster ${EKS_CLUSTER_NAME} --region ${AWS_REGION} | jq -r '.nodegroups[0]')
    echo "export EKS_NODEGROUP=${EKS_NODEGROUP}" | tee -a ~/.bash_profile

# Set EKS nodegroup worker node instance profile
    STACK_NAME=$(aws eks describe-nodegroup --cluster-name $EKS_CLUSTER_NAME --nodegroup-name ${EKS_NODEGROUP} | jq -r '.nodegroup.tags."aws:cloudformation:stack-name"')
    ROLE_NAME=$(aws cloudformation describe-stack-resources --stack-name $STACK_NAME | jq -r '.StackResources[] | select(.ResourceType=="AWS::IAM::Role") | .PhysicalResourceId')
    echo "export ROLE_NAME=${ROLE_NAME}" | tee -a ~/.bash_profile

# Enable IAM OIDC provider    
    eksctl utils associate-iam-oidc-provider --cluster ${EKS_CLUSTER_NAME} --region ${AWS_REGION} --approve

# Add unmanaged nodegroup for testing

    echo "Adding unmanaged node group"
    cat <<EOF > cluster-config.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: eksworkshop-eksctl
  region: ap-southeast-1
  version: "1.21"
nodeGroups:          
  - name: nodegroup2
    instanceType: t3.small
    desiredCapacity: 1
    privateNetworking: true
    volumeSize: 100
    volumeType: gp3                   
    volumeEncrypted: true
    tags:
      'eks:cluster-name': eksworkshop-eksctl
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: true
        ebs: true
        fsx: true
        efs: true
        albIngress: true
        xRay: true
        cloudWatch: true
EOF

    eksctl create nodegroup -f cluster-config.yaml --include=nodegroup2
    rm -f ./cluster-config.yaml 
    kubectl get node

# Install AWS Load Balancer Controller
    echo "Installing AWS Load Balancer Controller"
    curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.4.3/docs/install/iam_policy.json

    aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

    rm -rf iam_policy.json

    eksctl create iamserviceaccount \
    --cluster=${EKS_CLUSTER_NAME} \
    --namespace=kube-system \
    --name=aws-load-balancer-controller \
    --role-name "AmazonEKSLoadBalancerControllerRole" \
    --attach-policy-arn=arn:aws:iam::${ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy \
    --approve

    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName=${EKS_CLUSTER_NAME} \
    --set serviceAccount.create=false \
    --set serviceAccount.name=aws-load-balancer-controller 

# Clone lab repositories
    cd ~/environment
    git clone ${REPO_PATH}

# Install exam keep-alive application
    sed -i "s/$CANDIDATE_NAME/Anonymous/" keepalive/manifest.yml
    kubectl apply --server-side -f keepalive/manifest.yml
    KEEPALIVE_INGRESS=$(kubectl get ingress exam-keepalive -n exam -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    echo "export KEEPALIVE_INGRESS=${KEEPALIVE_INGRESS}" | tee -a ~/.bash_profile
  
    curl ${ADD_URL} -H "Content-Type: application/json" -X POST -d "{'Name': "$CANDIDATE_NAME", 'IngressURL': "$KEEPALIVE_INGRESS", 'AWSAccountID': $ACCOUNT_ID}" 

    
elif [[ "${EKS_CLUSTER_NAME}" = "" ]]
then

# Print a message if there's no EKS cluster
   echo "There are no EKS clusters provisioned in region: ${AWS_REGION}"

fi

# Print a message if there's no worker node instance profile set

if [[ "${ROLE_NAME}" = "" ]]
then

   echo "!!WARNING - Please set an EC2 instance profile for your worker nodes in the ${EKS_CLUSTER_NAME} cluster"

fi

# Update aws-auth ConfigMap granting cluster-admin to TeamRole (cluster creator is "eksworkshop-admin")
eksctl create iamidentitymapping \
  --cluster eksworkshop-eksctl \
  --arn arn:aws:iam::${ACCOUNT_ID}:role/TeamRole \
  --username cluster-admin \
  --group system:masters \
  --region ${AWS_REGION}

# cleanup
rm -vf ${HOME}/.aws/credentials
source ~/.bash_profile

echo "Your exam begins now. Good luck. "