data "google_client_config" "actual" {}

provider "helm" {
  kubernetes {
    host                   = "https://${google_container_cluster.nebula.endpoint}"
    token                  = data.google_client_config.actual.access_token
    cluster_ca_certificate = base64decode(google_container_cluster.nebula.master_auth[0].cluster_ca_certificate)
  }
}

resource "helm_release" "agones" {
  count            = var.instalar_agones ? 1 : 0
  name             = "agones"
  repository       = "https://agones.dev/chart/stable"
  chart            = "agones"
  version          = var.agones_version
  namespace        = "agones-system"
  create_namespace = true
  depends_on       = [google_container_node_pool.juego]

  set {
    name  = "agones.metrics.serviceMonitor.enabled"
    value = tostring(var.instalar_monitoreo)
  }
}

resource "helm_release" "monitoreo" {
  count            = var.instalar_monitoreo ? 1 : 0
  name             = "monitoreo"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  depends_on       = [google_container_node_pool.juego]

  set {
    name  = "prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues"
    value = "false"
  }

  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = "false"
  }
}
