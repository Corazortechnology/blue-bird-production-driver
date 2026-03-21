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

The command prints **one JSON object**. For **`azure/login@v2`** with a **service principal + password**, you must use **one** secret:

| Secret name | Value |
|-------------|--------|
| **`AZURE_CREDENTIALS`** | The **entire JSON** (one block), with **`clientId`**, **`clientSecret`**, **`subscriptionId`**, **`tenantId`** |

Official docs: [Login with a service principal secret](https://github.com/Azure/login#login-with-a-service-principal-secret).

**Why not four separate secrets?** If the workflow passes `client-id`, `tenant-id`, and `subscription-id` together, **`azure/login` treats that as OIDC** (federated identity) and **ignores** `creds`. Then login fails with *"client-id and tenant-id are not supplied"* unless OIDC is fully configured. **Password-based SP login uses `creds` only** — do not pass those three inputs at the same time.

If you already created four secrets, either:

- Build one JSON by hand and add **`AZURE_CREDENTIALS`**, or  
- Run `az ad sp create-for-rbac ... --sdk-auth` again and paste the full output into **`AZURE_CREDENTIALS`**.

Also ensure the SP can use ACR (Contributor on RG usually covers ACR in that RG). If the registry is in another RG, grant **AcrPush** on the registry to this SP.

## 2) GitHub repository secrets

1. Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**  
2. Name: **`AZURE_CREDENTIALS`**  
3. Value: paste the **full JSON** from `create-for-rbac --sdk-auth` (valid JSON, no trailing commas).

You may delete the four separate secrets (`AZURE_CLIENT_ID`, etc.) if you switch to **`AZURE_CREDENTIALS`** only — the workflow uses **`AZURE_CREDENTIALS`**.

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
