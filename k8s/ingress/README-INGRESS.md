# HTTPS on AKS — NGINX Ingress + cert-manager + Let’s Encrypt

**Goal:** `https://api.corazor.com/demo` (camera + `wss://` works).

## Prerequisites

- `kubectl` configured for your cluster  
- [Helm 3](https://helm.sh/docs/intro/install/) installed  
- DNS will point **`api.corazor.com`** → **Ingress controller public IP** (not the old `api-service` LB IP after you switch)

---

## Phase 1 — NGINX Ingress Controller

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
```

Wait for **EXTERNAL-IP**:

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller -w
```

Press Ctrl+C when you have an IP. **Use this IP** for DNS `api` A record (Phase 4).

---

## Phase 2 — cert-manager

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
```

Wait until pods are ready:

```bash
kubectl get pods -n cert-manager
```

---

## Phase 3 — Let’s Encrypt issuer

Edit **`cluster-issuer-prod.yaml`** — replace `YOUR_EMAIL@example.com` with a real address (Let’s Encrypt notifications).

Apply **staging** first (avoids rate limits while testing):

```bash
kubectl apply -f k8s/ingress/cluster-issuer-staging.yaml
```

When certificates work, switch Ingress annotation to **`letsencrypt-prod`** and apply **`cluster-issuer-prod.yaml`**.

---

## Phase 4 — DNS (GoDaddy)

Create **A record**:

| Host | Points to |
|------|-----------|
| **api** | **Ingress EXTERNAL-IP** (from Phase 1) |

TTL: 600 or default. Wait for propagation (minutes–hours).

---

## Phase 5 — Ingress for `api.corazor.com`

```bash
kubectl apply -f k8s/ingress/api-ingress.yaml
```

Check certificate:

```bash
kubectl get certificate -n default
kubectl describe certificate api-corazor-tls -n default
```

Test:

```bash
curl -s https://api.corazor.com/health
```

---

## Phase 6 (optional) — Save one Azure LB

When HTTPS works, you can change **`api-service`** from **LoadBalancer** to **ClusterIP** so only Ingress has a public IP. Edit `k8s/api-full.yaml` Service `type: ClusterIP`, apply, and rely on Ingress only.

---

## WebSocket

`api-ingress.yaml` includes long timeouts for `/stream`. If issues persist, increase `proxy-read-timeout` / `proxy-send-timeout`.
