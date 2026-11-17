variable "proyecto" {
  description = "ID del proyecto de Google Cloud"
  type        = string
}

variable "region" {
  description = "Región principal de despliegue en GCP"
  type        = string
  default     = "us-central1"
}

variable "tipo_maquina_juego" {
  description = "Tipo de máquina para el node pool de servidores de partida"
  type        = string
  default     = "e2-standard-4"
}

variable "nodos_juego" {
  description = "Nodos iniciales del pool de servidores de juego (3 para modo completo, 1 para modo reducido)"
  type        = number
  default     = 3
}

variable "min_nodos_juego" {
  description = "Mínimo de nodos en autoescalado"
  type        = number
  default     = 3
}

variable "max_nodos_juego" {
  description = "Máximo de nodos en autoescalado (12–20 modo completo, 3 modo reducido)"
  type        = number
  default     = 12
}

variable "redes_juego" {
  description = " Lista de rangos CIDR autorizados para conectarse a los puertos 7000-8000 de los GameServers"
  type        = list(string)
  validation {
    condition     = length(var.redes_juego) > 0 && alltrue([for red in var.redes_juego : can(cidrhost(red, 0)) && !contains(["0.0.0.0/0", "::/0"], red)])
    error_message = "Indica CIDR de laboratorio con acceso limitado (p. ej. la subred interna de la VM de Locust o tu IP/32)."
  }
}

variable "instalar_agones" {
  description = "Instalar Agones mediante Helm en el clúster GKE"
  type        = bool
  default     = true
}

variable "agones_version" {
  description = "Versión del chart de Agones compatible con Kubernetes 1.29/1.30 y Helm 3"
  type        = string
  default     = "1.44.0"
}

variable "instalar_monitoreo" {
  description = "Instalar kube-prometheus-stack (Prometheus + Grafana) mediante Helm"
  type        = bool
  default     = true
}

variable "crear_firestore" {
  description = "Crear la base de datos Firestore (default) si el proyecto aún no la tiene"
  type        = bool
  default     = false
}
