Kubernetes manifests for the zclonic app

Apply the manifests (ensure kubectl is configured to your cluster):

kubectl apply -f k8kamp/namespace.yaml
kubectl apply -f k8kamp/deployment.yaml
kubectl apply -f k8kamp/service.yaml
kubectl apply -f k8kamp/ingress.yaml

Notes:
- Replace `your-registry/zclonic:latest` in `deployment.yaml` with your image.
- Ensure an Ingress controller (e.g., nginx) is installed if you plan to use the Ingress manifest.
- Consider adding resource requests/limits and configuring horizontal pod autoscaling.
