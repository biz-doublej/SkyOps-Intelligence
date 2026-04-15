# SkyOps STAGING (single-node k3s or GKE preview)

terraform {
  required_version = ">= 1.6"
  required_providers {
    helm       = { source = "hashicorp/helm",       version = "~> 2.14" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.32" }
    google     = { source = "hashicorp/google",     version = "~> 5.34" }
  }
  backend "gcs" {
    bucket = "skyops-terraform-state"
    prefix = "staging"
  }
}

variable "project_id"    { type = string }
variable "region"        { type = string  default = "asia-northeast3" }
variable "cluster_name"  { type = string  default = "skyops-staging" }
variable "image_tag"     { type = string  default = "2.1.1" }

data "google_client_config" "current" {}

data "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region
  project  = var.project_id
}

provider "kubernetes" {
  host                   = "https://${data.google_container_cluster.primary.endpoint}"
  token                  = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(data.google_container_cluster.primary.master_auth[0].cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = "https://${data.google_container_cluster.primary.endpoint}"
    token                  = data.google_client_config.current.access_token
    cluster_ca_certificate = base64decode(data.google_container_cluster.primary.master_auth[0].cluster_ca_certificate)
  }
}

module "skyops" {
  source            = "../../modules/skyops"
  environment       = "staging"
  chart_values_file = "${path.module}/../../../k8s/helm/skyops/values.staging.yaml"
  image_tag         = var.image_tag
  image_registry    = "asia-northeast3-docker.pkg.dev/${var.project_id}/containers"
}
