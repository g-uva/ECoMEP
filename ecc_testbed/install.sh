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
kubectl --context k3d-cloud label node k3d-cloud-server-0 tier=cloud energy=grid       geo=us-virginia

# Install OpenFaaS + Prometheus into each Cluster
kubectl --context k3d-edge create namespace openfaas
kubectl --context k3d-edge create namespace openfaas-fn
helm repo add openfaas https://openfaas.github.io/faas-netes/
helm upgrade -i openfaas openfaas/openfaas \
     --namespace openfaas --kube-context k3d-edge \
     --set generateBasicAuth=true \
     --set gateway.service.type=LoadBalancer \
     --set prometheus.create=true


# fog cluster
kubectl --context k3d-fog create namespace openfaas
kubectl --context k3d-fog create namespace openfaas-fn
helm upgrade -i openfaas openfaas/openfaas \
  --namespace openfaas \
  --kube-context k3d-fog \
  --set generateBasicAuth=true \
  --set gateway.service.type=LoadBalancer \
  --set prometheus.create=true

# cloud cluster
kubectl --context k3d-cloud create namespace openfaas
kubectl --context k3d-cloud create namespace openfaas-fn
helm upgrade -i openfaas openfaas/openfaas \
  --namespace openfaas \
  --kube-context k3d-cloud \
  --set generateBasicAuth=true \
  --set gateway.service.type=LoadBalancer \
  --set prometheus.create=true

# This is what is outputted after we run the command before.
export PASSWORD="$(kubectl -n openfaas get secret basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode)"
# PASSWORD=$(kubectl --context=k3d-edge \
#     -n openfaas get secret basic-auth -o \
#     jsonpath="{.data.basic-auth-password}" | base64 -d)


# To run Docker:
docker build -t workload-producer:latest .
docker run --rm -e PASSWORD=$PASSWORD goncaloferreirauva/workload-faas:latest # This is assuming that the export PASSWORD previous command was ran.
