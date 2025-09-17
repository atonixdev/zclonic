variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "s3_bucket_name" {
  type = string
}

variable "kubeconfig_path" {
  type    = string
  default = "~/.kube/config"
}

variable "kubeconfig_context" {
  type    = string
  default = ""
}

variable "namespace" {
  type    = string
  default = "zclonic"
}

variable "image" {
  type    = string
  default = "your-registry/zclonic:latest"
}

variable "replicas" {
  type    = number
  default = 2
}
