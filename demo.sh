#!/usr/bin/env bash
# Demo helper (bash / Git Bash).
#   ./demo.sh up        local kind cluster + ingress-nginx + Prometheus + Grafana + load generator
#   ./demo.sh jenkins   build and start Jenkins in Docker, wired to the cluster (needs REPO_URL)
#   ./demo.sh gke       same add-ons on the GKE cluster from terraform/, plus a kubeconfig for Jenkins
#   ./demo.sh down      delete the kind cluster and the Jenkins container
set -euo pipefail
cd "$(dirname "$0")"
export MSYS_NO_PATHCONV=1  # stop Git Bash from rewriting /var/run/docker.sock, /root/... into Windows paths

CLUSTER=canary-demo
INGRESS_NGINX=https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider

addons() {
  kubectl apply -f "$INGRESS_NGINX/$1/deploy.yaml"
  kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=300s
  kubectl create configmap grafana-dashboard --from-file=grafana/dashboard.json --dry-run=client -o yaml | kubectl apply -f -
  kubectl create configmap loadgen --from-file=scripts/loadgen.py --from-file=ml/data.py --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply -f k8s/monitoring.yaml -f k8s/loadgen.yaml
}

case "${1:-}" in
  up)
    kind create cluster --config kind-config.yaml
    kubectl label node "$CLUSTER-control-plane" ingress-ready=true  # the kind ingress-nginx manifest schedules on this label
    addons kind
    echo "App http://localhost:8000 (404 until the first release) | Grafana http://localhost:3000 | Prometheus http://localhost:9090"
    ;;

  jenkins)
    : "${REPO_URL:?set REPO_URL to your GitHub repo, e.g. REPO_URL=https://github.com/you/repo.git ./demo.sh jenkins}"
    docker build -t canary-jenkins jenkins
    docker rm -f jenkins >/dev/null 2>&1 || true
    net=""
    docker network inspect kind >/dev/null 2>&1 && net="--network=kind"  # so Jenkins can reach the kind node by name
    docker run -d --name jenkins $net -p 127.0.0.1:8080:8080 \
      -v jenkins_home:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock \
      -e REPO_URL="$REPO_URL" -e REGISTRY="${REGISTRY:-}" \
      -e INGRESS_URL="${INGRESS_URL:-http://$CLUSTER-control-plane}" \
      -e JENKINS_ADMIN_PASSWORD="${JENKINS_ADMIN_PASSWORD:-admin}" \
      canary-jenkins
    docker exec jenkins mkdir -p /root/.kube
    if [ -n "${KUBECONFIG_FILE:-}" ]; then
      docker cp "$KUBECONFIG_FILE" jenkins:/root/.kube/config
    else
      docker exec jenkins sh -c "kind get kubeconfig --internal --name $CLUSTER > /root/.kube/config"
    fi
    if [ -n "${REGISTRY:-}" ]; then  # Artifact Registry login; the token lasts about an hour
      gcloud auth print-access-token | docker exec -i jenkins docker login -u oauth2accesstoken --password-stdin "https://${REGISTRY%%/*}"
    fi
    echo "Jenkins http://localhost:8080 (admin / ${JENKINS_ADMIN_PASSWORD:-admin}). Click 'Build Now' on canary-release once."
    ;;

  gke)
    eval "$(terraform -chdir=terraform output -raw get_credentials)"
    addons cloud
    # Jenkins gets a token for a namespaced service account instead of needing gcloud inside its container.
    kubectl create serviceaccount jenkins --dry-run=client -o yaml | kubectl apply -f -
    kubectl create rolebinding jenkins-edit --clusterrole=edit --serviceaccount=default:jenkins --dry-run=client -o yaml | kubectl apply -f -
    server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
    ca=$(kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
    token=$(kubectl create token jenkins --duration=24h)
    cat > gke-kubeconfig <<EOF
apiVersion: v1
kind: Config
clusters: [{name: gke, cluster: {server: "$server", certificate-authority-data: "$ca"}}]
users: [{name: jenkins, user: {token: "$token"}}]
contexts: [{name: gke, context: {cluster: gke, user: jenkins, namespace: default}}]
current-context: gke
EOF
    ip=""
    until [ -n "$ip" ]; do
      sleep 5
      ip=$(kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    done
    echo "Now run:"
    echo "  KUBECONFIG_FILE=gke-kubeconfig REGISTRY=$(terraform -chdir=terraform output -raw registry) INGRESS_URL=http://$ip REPO_URL=<your repo> ./demo.sh jenkins"
    ;;

  down)
    docker rm -f jenkins >/dev/null 2>&1 || true
    kind delete cluster --name "$CLUSTER"
    ;;

  *)
    echo "usage: $0 up | jenkins | gke | down" >&2
    exit 1
    ;;
esac
