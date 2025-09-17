terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.10.0"
    }
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
  config_context = var.kubeconfig_context
}

resource "kubernetes_namespace" "zclonic" {
  metadata {
    name = var.namespace
  }
}

resource "kubernetes_deployment" "zclonic" {
  metadata {
    name = "zclonic-app"
    namespace = kubernetes_namespace.zclonic.metadata[0].name
    labels = {
      app = "zclonic"
    }
  }

  spec {
    replicas = var.replicas
    selector {
      match_labels = {
        app = "zclonic"
      }
    }
    template {
      metadata {
        labels = {
          app = "zclonic"
        }
      }
      spec {
        container {
          image = var.image
          name  = "zclonic"
          port {
            container_port = 5000
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "zclonic" {
  metadata {
    name = "zclonic-svc"
    namespace = kubernetes_namespace.zclonic.metadata[0].name
  }
  spec {
    selector = {
      app = "zclonic"
    }
    port {
      port = 80
      target_port = 5000
    }
    type = "ClusterIP"
  }
}
