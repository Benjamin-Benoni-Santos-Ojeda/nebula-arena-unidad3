variable "region" {
  description = "Región de AWS para el despliegue"
  type        = string
  default     = "us-east-2"
}

variable "tipo_instancia_juego" {
  description = "Tipo de instancia EC2 elegible en Free Tier (m7i-flex.large: 2 vCPU, 8 GB RAM)"
  type        = string
  default     = "m7i-flex.large"
}

variable "nodos_juego" {
  description = "Número inicial de nodos en el node group de juego"
  type        = number
  default     = 3
}

variable "min_nodos_juego" {
  description = "Mínimo de nodos en autoescalado"
  type        = number
  default     = 2
}

variable "max_nodos_juego" {
  description = "Máximo de nodos en autoescalado (respetando cuota de 32 vCPU)"
  type        = number
  default     = 5
}
