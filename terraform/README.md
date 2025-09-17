Terraform for deploying to Kubernetes via the Kubernetes provider

This Terraform configuration uses the Kubernetes provider to apply a Namespace, Deployment, and Service directly to a cluster using your kubeconfig.

Usage:
```
cd terraform
terraform init
terraform plan -var='kubeconfig_path="~/.kube/config"' -var='image="your-registry/zclonic:latest"'
terraform apply -var='kubeconfig_path="~/.kube/config"' -var='image="your-registry/zclonic:latest"'
```

Variables:
- `kubeconfig_path` - path to your kubeconfig file (default `~/.kube/config`).
- `kubeconfig_context` - optional kubeconfig context to use.
- `namespace` - Kubernetes namespace to create (default `zclonic`).
- `image` - container image to deploy.
- `replicas` - number of replicas for the deployment.

Notes:
- You must have `kubectl` configured and access to the cluster referenced by the kubeconfig.
- Terraform will create resources in the target cluster.
- For production, consider using a CI/CD pipeline and apply via an account with limited privileges.
