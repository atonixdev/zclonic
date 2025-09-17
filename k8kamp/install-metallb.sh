#!/usr/bin/env bash
set -euo pipefail

# Downloads the official MetalLB manifest and applies it, then applies the local metallb-config
# Usage: ./install-metallb.sh

MANIFEST_URL="https://raw.githubusercontent.com/metallb/metallb/main/config/manifests/metallb-native.yaml"
TMP_MANIFEST="/tmp/metallb-native.yaml"

echo "Downloading MetalLB manifest from ${MANIFEST_URL}"
curl -fsSL ${MANIFEST_URL} -o "${TMP_MANIFEST}"

echo "Applying MetalLB manifest"
kubectl apply -f "${TMP_MANIFEST}"

echo "Applying local MetalLB config"
kubectl apply -f metallb-config.yaml -n metallb-system

echo "Done. MetalLB should be installed. Check pods in metallb-system namespace."
kubectl -n metallb-system get pods
