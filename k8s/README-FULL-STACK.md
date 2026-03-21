# Full stack on AKS: DB + full API + WebSocket live stream

## Architecture (this repo)

| Piece | Where it runs |
|--------|----------------|
| **MongoDB** | Use **MongoDB Atlas** (recommended) or any reachable `mongodb://` / `mongodb+srv://` URL |
| **REST + WebSocket** | **One “fat” API pod** — `app.api.main:app` loads all routers + **`data_pipeline/websocket.py`** |
| **Live ML (faces, fatigue, distraction, fusion)** | **Inside that API process** (same as local dev) — **not** the separate `ml-service` container |
| **ml-service** | Optional extra; you can **`kubectl scale deployment ml-service --replicas=0`** to save CPU/RAM |

WebSocket endpoint (after deploy):

- `ws://<LOAD_BALANCER_IP>/stream`  
- Optional query: `?driver_id=<id>`

---

## 1) Security: MongoDB credentials

1. **Rotate** any password that was ever committed to `config.yaml` (Atlas → Database Access).
2. **Atlas Network Access**: allow your AKS outbound IPs, or `0.0.0.0/0` for testing only.

---

## 2) Create the Kubernetes Secret

```bash
kubectl create secret generic driver-safety-secrets \
  --from-literal=MONGODB_URL='mongodb+srv://USER:PASSWORD@cluster.mongodb.net/?retryWrites=true&w=majority' \
  --from-literal=MONGODB_DATABASE='driver_monitoring' \
  --dry-run=client -o yaml | kubectl apply -f -
```

(Use your real URI; no spaces around `=`.)

---

## 3) Build and push the **full** API image

From repo root (Apple Silicon → build **amd64** for AKS):

```bash
docker build --platform linux/amd64 -f Dockerfile.full -t api-service:full-2.0 .

docker tag api-service:full-2.0 YOUR_ACR.azurecr.io/api-service:full-2.0
docker push YOUR_ACR.azurecr.io/api-service:full-2.0
```

Replace `YOUR_ACR` with your registry name.

---

## 4) Free the node (important on 1× small node)

The full API needs **several GB RAM**. Scale down the **thin** API and optional **ml-service** before applying the full Deployment:

```bash
kubectl delete deployment api-service --ignore-not-found
# If you had the thin api only, name might still be api-service — backup old yaml if needed.

kubectl scale deployment ml-service --replicas=0
```

Remove HPA if it targets `api-service` (it will fight single-replica or OOM):

```bash
kubectl delete hpa api-service --ignore-not-found
```

---

## 5) Apply full API

Edit `k8s/api-full.yaml` if your ACR name differs, then:

```bash
kubectl apply -f k8s/api-full.yaml
kubectl rollout status deployment/api-service
kubectl get pods -l app=api-service
kubectl get svc api-service
```

Wait for `EXTERNAL-IP`.

---

## 6) Quick checks

```bash
curl -s http://EXTERNAL_IP/health
curl -s http://EXTERNAL_IP/
```

---

## 7) **Watch** the live pipeline (WebSocket client)

On a machine with a **camera** and repo + deps installed:

```bash
cd /path/to/Blue-bird-driver-safety-main\ 2
pip install -r requirements.txt
python -m data_pipeline.client --url ws://EXTERNAL_IP/stream --source 0
```

Protocol (same as `data_pipeline/client.py`):

- Client → server: **binary** JPEG frames  
- Server → client: **text** JSON (metrics), then **binary** JPEG (composite)

Press **`x`** to quit, **`r`** to recalibrate.

---

## 8) If the pod crashes (OOM / CrashLoop)

- Increase node VM size or add a node pool with **more RAM**.
- Lower `MODEL_INTERVAL` in `data_pipeline/websocket.py` (less frequent model runs) for testing.
- Check logs: `kubectl logs -f deployment/api-service`

---

## Models

`models/arcface.onnx` is copied into the image. For other checkpoints, add them under `models/` and rebuild.
