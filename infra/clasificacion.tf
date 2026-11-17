variable "imagen_clasificacion" {
  description = "Imagen publicada de la clasificación. Null omite el servicio."
  type        = string
  default     = null
}

variable "identidad_clasificacion" {
  description = "Correo de la cuenta de servicio con permiso en el Firestore del laboratorio."
  type        = string
  default     = null
}

resource "google_firestore_database" "scores" {
  count       = var.crear_firestore ? 1 : 0
  project     = var.proyecto
  name        = "(default)"
  location_id = "nam5"
  type        = "FIRESTORE_NATIVE"
}

resource "google_cloud_run_v2_service" "clasificacion" {
  count               = var.imagen_clasificacion == null ? 0 : 1
  name                = "nebula-leaderboard-${terraform.workspace}"
  location            = var.region
  deletion_protection = false

  template {
    service_account = var.identidad_clasificacion
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
    containers {
      image = var.imagen_clasificacion
    }
  }

  lifecycle {
    precondition {
      condition     = var.identidad_clasificacion != null
      error_message = "Indica una cuenta de servicio dedicada con acceso a Firestore."
    }
  }
}

output "url_clasificacion" {
  value = one(google_cloud_run_v2_service.clasificacion[*].uri)
}
