resource "google_container_cluster" "nebula" {
  name                     = "nebula-${terraform.workspace}"
  location                 = "${var.region}-a"
  network                  = google_compute_network.vpc.id
  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false
}

resource "google_container_node_pool" "juego" {
  name               = "game-pool"
  location           = google_container_cluster.nebula.location
  cluster            = google_container_cluster.nebula.name
  initial_node_count = var.nodos_juego

  autoscaling {
    min_node_count = var.min_nodos_juego
    max_node_count = var.max_nodos_juego
  }

  node_config {
    machine_type = var.tipo_maquina_juego
    tags         = ["game-server"]
    labels       = { rol = "juego" }
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}

resource "google_artifact_registry_repository" "imagenes" {
  location      = var.region
  repository_id = "nebula"
  format        = "DOCKER"
}
