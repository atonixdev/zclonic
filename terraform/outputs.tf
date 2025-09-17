output "s3_bucket_name" {
  value = aws_s3_bucket.static_assets.bucket
}

output "k8s_namespace" {
  value = kubernetes_namespace.zclonic.metadata[0].name
}

output "k8s_service" {
  value = kubernetes_service.zclonic.metadata[0].name
}
