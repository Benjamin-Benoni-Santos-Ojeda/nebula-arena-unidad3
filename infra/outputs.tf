output "cluster" {
  value = google_container_cluster.nebula.name
}

output "ubicacion_cluster" {
  value = google_container_cluster.nebula.location
}

output "registro" {
  value = "${var.region}-docker.pkg.dev/${var.proyecto}/nebula"
}
