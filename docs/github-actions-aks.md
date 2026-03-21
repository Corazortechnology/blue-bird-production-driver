# GitHub Actions → AKS (automatic deploy on push to `main`)

The workflow [`.github/workflows/deploy-aks.yml`](../.github/workflows/deploy-aks.yml):

1. Checks out the repo  
2. Logs into Azure  
3. Builds **`Dockerfile.full`** for **`linux/amd64`**  
4. Pushes **`bluebirddriversafetyacr.azurecr.io/api-service:<git-sha>`** and **`:latest`**  
5. Runs **`kubectl set image`** on **`deployment/api-service`** in **`default`** and waits for rollout  

## 1) Azure service principal (one-time)

Create an app registration + service principal with rights to:

- **ACR**: push images (e.g. **AcrPush** on the registry)  
- **AKS**: get cluster credentials and deploy (e.g. **Azure Kubernetes Service Cluster User Role** on the cluster, or **Contributor** on the resource group for simplicity)

Example (Contributor on the resource group — simple; tighten later):

```bash
SUBSCRIPTION_ID="<your-subscription-id>"
RG="rg-bluebird-driver-safety"

az ad sp create-for-rbac --name "github-actions-bluebird-aks" \
  --role contributor \
  --scopes /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG} \
  --sdk-auth
```

The command prints JSON. **Add it to GitHub** as repository secret:

| Secret name | Value |
|-------------|--------|
| `AZURE_CREDENTIALS` | The **full JSON** output from `create-for-rbac --sdk-auth` |

Also ensure the SP can pull from ACR (Contributor on RG usually covers ACR in that RG). If the registry is in another RG, grant **AcrPush** on the registry resource to this SP.

## 2) GitHub repository secrets

1. Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**  
2. Name: **`AZURE_CREDENTIALS`**  
3. Value: paste the JSON from step 1  

No other secrets are required for the default workflow.

## 3) OIDC (optional, no client secret)

To avoid a long-lived secret, use **Workload identity federation** (Entra federated credential for GitHub). Then switch the workflow’s Azure login step to the OIDC style from [Azure/login](https://github.com/Azure/login#login-with-openid-connect-oidc-recommended) and remove `creds:`.

## 4) Old App Service workflow

[`.github/workflows/main_blue-bird-driver.yml`](../.github/workflows/main_blue-bird-driver.yml) deploys a **zip** to **Azure App Service**. If you only use **AKS** now, **disable or delete** that workflow so you don’t deploy twice or to the wrong place.

Options:

- Delete the file, or  
- Rename to `*.disabled`, or  
- Change `on.push.branches` to a branch you never use  

## 5) After push

On every push to **`main`**, Actions builds and deploys. Check **Actions** tab for logs.

Manual run: **Actions** → **Build and deploy to AKS** → **Run workflow**.

## 6) Tuning

Edit env vars at the top of `deploy-aks.yml` if your names differ:

- `ACR_NAME`, `ACR_LOGIN_SERVER`, `IMAGE_NAME`  
- `AKS_RG`, `AKS_NAME`, `K8S_NAMESPACE`, `DEPLOYMENT_NAME`, `CONTAINER_NAME`  

The Deployment must already exist (`kubectl apply -f k8s/api-full.yaml` once); the workflow only **updates the image**.
