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

#title           submit.sh
#description     This script will submit the exam result
#author          Bingjiao Yu (@bingjiao)
#contributors    
#date            2022-10-08
#version         0.1
#usage           ./submit.sh
#==============================================================================

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
echo "export ACCOUNT_ID=${ACCOUNT_ID}" | tee -a ~/.bash_profile

# Hard-coded URL to submit result
SUBMIT_URL=https://je5rwctnad.execute-api.ap-southeast-1.amazonaws.com/Prod/submit

# Get ingress path for test
TEST_INGRESS=$(kubectl get ingress exam-test -n exam -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

if [ -z $TEST_INGRESS ]; 
then 
    echo "You haven't deploy the test application or I can't find it. Don't change the name of Ingress since it's hardcoded."
else    
    jq -n \      
        --arg url "$KEEPALIVE_INGRESS"\
        --arg id "$ACCOUNT_ID"\
        '{URL: $url, AWSAccountID: $id}'  > /tmp/submit.json

    curl ${SUBMIT_URL} -H "Content-Type: application/json" -X POST -d @/tmp/submit.json
fi




