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

IPv6 / MetalLB notes (bare-metal)
--------------------------------
- This directory includes a MetalLB config (`metalLB/metallb-config.yaml`) that defines an IPv6 address pool (ULA range). Update the IPv6 range to one routable on your LAN before applying.
- Install MetalLB into your cluster (apply the official MetalLB manifest) and then apply the `metalLB/metallb-config.yaml` to create the IPv6 pool.

Apply order for dual-stack setup (high level):
1. Ensure your kubeadm cluster was initialized with dual-stack service/pod CIDRs (serviceSubnet and podSubnet include IPv6 ranges).
2. Install a dual-stack capable CNI (Calico or Cilium) configured for your pod IPv6 range.
3. Install MetalLB and apply `k8kamp/metalLB/metallb-config.yaml` (update ranges first).
4. Deploy the zclonic manifests (`namespace`, `deployment`, `service`, `ingress`). The `service.yaml` is annotated to request the MetalLB IPv6 pool and prefers dual-stack.
5. Create DNS AAAA records pointing your hostname to the IPv6 address assigned to the LoadBalancer.

If you want, I can add the MetalLB official manifest here (downloaded copy) or patch the ingress controller Service to be LoadBalancer-managed by MetalLB.
