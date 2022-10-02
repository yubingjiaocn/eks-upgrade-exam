<<<<<<< HEAD
# Scripts and Applications use for EKS upgrade exam

## Init

run `eksinit.sh`

## Test app #1 (keepalive)

A Flask app. When accessed, it will return candidate's name (in env var), current cluster's control plane version and node version. 

## Test app #2 (deploy)

Another Flask app. When accessed, send request to backend for submission. 

## Backend 

Several lambda function for monitor test app #1 and keep record for examtakers. 

=======
# eks-upgrade-exam
>>>>>>> 199dc710afbea0e233e6cb016693c3ce62b25364
