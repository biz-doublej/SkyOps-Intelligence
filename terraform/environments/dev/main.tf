# SkyOps DEV environment (Docker Desktop / local k3s)
# ============================================================================
# Usage:
#   cd terraform/environments/dev
#   export KUBECONFIG=~/.kube/config
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.6"
  required_providers {
    helm       = { source = "hashicorp/helm",       version = "~> 2.14" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.32" }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

variable "kubeconfig_path" {
  type    = string
  default = "~/.kube/config"
}

variable "kube_context" {
  type    = string
  default = "docker-desktop"
}

module "skyops" {
  source            = "../../modules/skyops"
  environment       = "dev"
  chart_values_file = "${path.module}/../../../k8s/helm/skyops/values.dev.yaml"
  image_tag         = "2.1.1"
  image_registry    = ""  # local build
  secrets           = {}  # dev: empty, use mock
}

output "skyops_dev_info" {
  value = {
    namespace    = module.skyops.namespace
    release_name = module.skyops.release_name
  }
}
