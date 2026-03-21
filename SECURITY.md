# Security notes

- **MongoDB**: If a connection string was ever committed to git, **rotate the password** in MongoDB Atlas (or your host) and use **Kubernetes Secrets** + `MONGODB_URL` / `MONGODB_DATABASE` (see `k8s/README-FULL-STACK.md`).
- Never commit `.env` files with production credentials.
