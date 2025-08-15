# Ubuntu / macOS
curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash
brew install helm           # or: sudo snap install helm --classic
curl -sL https://cli.openfaas.com | sudo sh      # faas-cli

# Edge  (1 server + 1 agent)
k3d cluster create edge \
      --servers 1 --agents 1 \
      --port "31110:31112@agent:0"

# Fog   (2 nodes)
k3d cluster create fog  --servers 1 --agents 1 --port "31120:31112@agent:0"

# Cloud (3 nodes, defaults)
k3d cluster create cloud --agents 2 --port "31130:31112@agent:0"

# EDGE   → http://localhost:31110
# FOG    → http://localhost:31120
# CLOUD  → http://localhost:31130

# Labelling the clusters.
kubectl --context k3d-edge  label node k3d-edge-server-0  tier=edge  energy=renewable  geo=nl-amsterdam
kubectl --context k3d-fog   label node k3d-fog-server-0   tier=fog   energy=mixed      geo=de-frankfurt
kubectl --context k3d-cloud label node k3d-cloud-server-0 tier=cloud energy=grid       geo=fr-paris




# --------------------------------
# Experiment with Serverless OpenFaaS
# --------------------------------

# # Install OpenFaaS + Prometheus into each Cluster
# kubectl --context k3d-edge create namespace openfaas
# kubectl --context k3d-edge create namespace openfaas-fn
# helm repo add openfaas https://openfaas.github.io/faas-netes/
# helm upgrade -i openfaas openfaas/openfaas \
#      --namespace openfaas --kube-context k3d-edge \
#      --set generateBasicAuth=true \
#      --set gateway.service.type=LoadBalancer \
#      --set prometheus.create=true


# # fog cluster
# kubectl --context k3d-fog create namespace openfaas
# kubectl --context k3d-fog create namespace openfaas-fn
# helm upgrade -i openfaas openfaas/openfaas \
#   --namespace openfaas \
#   --kube-context k3d-fog \
#   --set generateBasicAuth=true \
#   --set gateway.service.type=LoadBalancer \
#   --set prometheus.create=true

# # cloud cluster
# kubectl --context k3d-cloud create namespace openfaas
# kubectl --context k3d-cloud create namespace openfaas-fn
# helm upgrade -i openfaas openfaas/openfaas \
#   --namespace openfaas \
#   --kube-context k3d-cloud \
#   --set generateBasicAuth=true \
#   --set gateway.service.type=LoadBalancer \
#   --set prometheus.create=true

# # This is what is outputted after we run the command before.
# export PASSWORD="$(kubectl -n openfaas get secret basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode)"

# # Password to login into open-faas
# export PASSWORD_FAAS=$(kubectl --context=k3d-edge \
#     -n openfaas get secret basic-auth -o \
#     jsonpath="{.data.basic-auth-password}" | base64 -d)


# # To run Docker with the Workload image:
# docker build -t goncaloferreirauva/workload-faas:latest -f ./Dockerfile.work .
# docker run --rm -e PASSWORD=$PASSWORD goncaloferreirauva/workload-faas:latest # This is assuming that the export PASSWORD previous command was ran.

# # Scheduler image run
# docker build -t goncaloferreirauva/sched-faas:latest -f ./Dockerfile.sched .
# docker run -d --name scheduler --network host -e PASS=$PASSWORD goncaloferreirauva/sched-faas:latest

# # Log into open-faas
# faas-cli login --gateway http://localhost:31110 --password="$PASSWORD_FAAS"

# # Build and deploy faas-cli and define gateway
# faas-cli build -f stack.yaml
# faas-cli deploy -f stack.yaml --gateway http://localhost:31110


# # 1) All three K3d clusters should show the core pods running
# kubectl --context k3d-edge   get pods -A
# kubectl --context k3d-fog    get pods -A
# kubectl --context k3d-cloud  get pods -A

# # Look for: gateway, queue-worker, prometheus (openfaas)  +  resize (openfaas-fn)

# # 2) OpenFaaS gateways reachable?
# curl -s http://localhost:31110/system/functions   # edge
# curl -s http://localhost:31120/system/functions   # fog
# curl -s http://localhost:31130/system/functions   # cloud

# # 3) Function replicas & invocation counts
# faas-cli list --gateway http://localhost:31110   # edge
# faas-cli list --gateway http://localhost:31120   # fog
# faas-cli list --gateway http://localhost:31130   # cloud

# # 4) Scheduler & workload containers running locally
# docker ps --format '{{.Names}}' | grep -E 'scheduler|workload'

# # 5) Queue-worker processing events (edge example)
# kubectl --context k3d-edge logs deploy/queue-worker -n openfaas --tail=5

