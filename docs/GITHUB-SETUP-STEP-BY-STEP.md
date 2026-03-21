# Step-by-step: GitHub repo + Azure secret + first push

Follow these in order. **You** must run the Azure and GitHub web steps; terminal commands are copy-paste.

---

## Part A — Create the empty repo on GitHub (website)

1. Open **https://github.com/new**
2. **Repository name:** e.g. `Blue-bird-driver-safety` (any name you like)
3. Choose **Private** or **Public**
4. **Do NOT** add README, .gitignore, or license (this folder already has files)
5. Click **Create repository**

6. Copy your repo URL. It looks like one of these:
   - HTTPS: `https://github.com/YOUR_USERNAME/YOUR_REPO.git`
   - SSH: `git@github.com:YOUR_USERNAME/YOUR_REPO.git`

Keep it for **Part D**.

---

## Part B — Azure service principal for GitHub Actions

This lets Actions log into Azure, push to ACR, and deploy to AKS.

### B1. Log in to Azure CLI (your Mac)

```bash
az login
az account show --query id -o tsv
```

Copy the **subscription id** (you already used `526a5e54-cfb0-41e9-a2d7-f24984359d44` before — use yours if different).

### B2. Create the service principal

Replace `SUBSCRIPTION_ID` with your subscription id.

```bash
SUBSCRIPTION_ID="526a5e54-cfb0-41e9-a2d7-f24984359d44"
RG="rg-bluebird-driver-safety"

az ad sp create-for-rbac \
  --name "github-actions-bluebird-aks" \
  --role contributor \
  --scopes /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG} \
  --sdk-auth
```

**Important:** The command prints **one JSON object**. Copy **the entire JSON** (from `{` to `}`). You will paste it into GitHub in Part C.

> If `create-for-rbac` fails, ensure your account can create app registrations in Entra ID.

### B3. (Optional) Tighter permissions later

`Contributor` on the resource group is simple. For production you can narrow to **AcrPush** on the registry + **Azure Kubernetes Service Cluster User Role** on the AKS cluster only.

---

## Part C — GitHub secret `AZURE_CREDENTIALS` (one JSON)

The workflow uses **`azure/login`** with **`creds`** — **one** secret whose value is the **full JSON** from Part B2 (`create-for-rbac --sdk-auth`), including **`clientId`**, **`clientSecret`**, **`subscriptionId`**, **`tenantId`**.

1. Repo → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** (or edit existing)
3. Name: **`AZURE_CREDENTIALS`**
4. Value: paste the **entire JSON** (single object)

Do **not** rely on four separate secrets for this workflow; [azure/login](https://github.com/Azure/login#login-with-a-service-principal-secret) expects the JSON in **`creds`**. If you set `client-id` + `tenant-id` + `subscription-id` without OIDC, login breaks.

---

## Part D — Connect your computer to GitHub and push

Run these **on your Mac** in the project folder. Replace `YOUR_GITHUB_REPO_URL` with the URL from Part A.

```bash
cd "/Users/tusharjain/Downloads/Blue-bird-driver-safety-main 2"

git remote add origin YOUR_GITHUB_REPO_URL
```

If `origin` already exists and is wrong:

```bash
git remote remove origin
git remote add origin YOUR_GITHUB_REPO_URL
```

First commit and push:

```bash
git add -A
git status
git commit -m "Initial commit: app, k8s, GitHub Actions deploy to AKS"
git branch -M main
git push -u origin main
```

- If GitHub asks for login, use a **Personal Access Token** (HTTPS) or SSH keys (SSH URL).
- Create a token: GitHub → **Settings** → **Developer settings** → **Personal access tokens** → generate with **repo** scope.

---

## Part E — Confirm the workflow ran

1. GitHub repo → **Actions**
2. Open **Build and deploy to AKS**
3. The run triggered by your push should be **green** (or read the error log)

If it fails on **Azure login**, check **`AZURE_CREDENTIALS`** is valid JSON with all four keys.  
If it fails on **kubectl**, check the SP has rights to the AKS cluster in `rg-bluebird-driver-safety`.

---

## Quick reference

| Step | Where | What |
|------|--------|------|
| 1 | github.com/new | Create empty repo |
| 2 | Terminal | `az ad sp create-for-rbac ... --sdk-auth` |
| 3 | GitHub → Secrets | **`AZURE_CREDENTIALS`** = full JSON (see Part C) |
| 4 | Terminal | `git remote add` + `git push` |

---

## Files that matter for deploy

- [`.github/workflows/deploy-aks.yml`](../.github/workflows/deploy-aks.yml) — CI/CD  
- [`docs/github-actions-aks.md`](github-actions-aks.md) — extra detail  
- [`Dockerfile.full`](../Dockerfile.full) — image build  

After every **push to `main`**, the workflow rebuilds the image and updates **`deployment/api-service`** on AKS.
