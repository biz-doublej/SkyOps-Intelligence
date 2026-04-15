# SkyOps Intelligence — Terraform module (P8-D · 2026-04-15)
# ============================================================================
# Reusable module — deploys SkyOps via Helm to an existing GKE cluster.
# Per-environment wiring lives in terraform/environments/{dev,staging,prod}/.
#
# Caller must provide:
#   - provider configuration (google, kubernetes, helm)
#   - secrets (SWIM/KAC/vLLM) via external_secrets or inline
#
# See also:
#   environments/dev/main.tf
#   environments/staging/main.tf
#   environments/prod/main.tf

terraform {
  required_version = ">= 1.6"
  required_providers {
    helm       = { source = "hashicorp/helm",       version = "~> 2.14" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.32" }
    random     = { source = "hashicorp/random",     version = "~> 3.6" }
  }
}

variable "environment" {
  description = "dev | staging | prod"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace for SkyOps"
  type        = string
  default     = "skyops"
}

variable "release_name" {
  description = "Helm release name"
  type        = string
  default     = "skyops"
}

variable "chart_path" {
  description = "Path to the helm chart"
  type        = string
  default     = "../../../k8s/helm/skyops"
}

variable "chart_values_file" {
  description = "Environment-specific values file"
  type        = string
}

variable "image_tag" {
  description = "Override api/dashboard image tag"
  type        = string
  default     = "2.1.1"
}

variable "image_registry" {
  description = "Container registry prefix"
  type        = string
  default     = ""
}

variable "secrets" {
  description = "Secret values (SWIM / KAC / vLLM). Empty map uses ExternalSecrets."
  type        = map(string)
  default     = {}
  sensitive   = true
}

# ── Namespace with PSA labels ─────────────────────────────────────────
resource "kubernetes_namespace" "skyops" {
  metadata {
    name = var.namespace
    labels = {
      "app"                                        = "skyops"
      "env"                                        = var.environment
      "pod-security.kubernetes.io/enforce"         = "restricted"
      "pod-security.kubernetes.io/enforce-version" = "latest"
      "pod-security.kubernetes.io/audit"           = "restricted"
      "pod-security.kubernetes.io/warn"            = "restricted"
    }
  }
}

# ── Inline secrets (optional — prefer ExternalSecrets) ────────────────
resource "kubernetes_secret" "swim" {
  count = contains(keys(var.secrets), "SWIM_PASSWORD") ? 1 : 0
  metadata {
    name      = "skyops-swim-secret"
    namespace = kubernetes_namespace.skyops.metadata[0].name
  }
  data = {
    SWIM_USERNAME = lookup(var.secrets, "SWIM_USERNAME", "")
    SWIM_PASSWORD = lookup(var.secrets, "SWIM_PASSWORD", "")
  }
  type = "Opaque"
}

# ── Helm release ─────────────────────────────────────────────────────
resource "helm_release" "skyops" {
  name       = var.release_name
  chart      = var.chart_path
  namespace  = kubernetes_namespace.skyops.metadata[0].name
  wait       = true
  timeout    = 600

  values = [
    file(var.chart_values_file),
  ]

  set {
    name  = "global.environment"
    value = var.environment
  }
  set {
    name  = "global.imageRegistry"
    value = var.image_registry
  }
  set {
    name  = "api.image.tag"
    value = var.image_tag
  }
  set {
    name  = "dashboard.image.tag"
    value = var.image_tag
  }
}

output "namespace" {
  value = kubernetes_namespace.skyops.metadata[0].name
}

output "release_name" {
  value = helm_release.skyops.name
}

output "ingress_host" {
  value = "(see helm values ingress.host)"
}
