# Infraestructura de Nebula Arena (`infra/`)

Este módulo de Terraform provisiona de forma reproducible la infraestructura de Google Cloud para **Nebula Arena**:

- **`main.tf` y `backend.tf`**: Proveedores `hashicorp/google` (`~> 6.0`) y `hashicorp/helm` (`~> 2.13`) y estado remoto en Google Cloud Storage (`backend "gcs"`) con soporte de bloqueo de estado.
- **`red.tf`**: Red VPC `nebula-vpc` y regla de firewall `nebula-gameservers` para TCP y UDP en los puertos `7000–8000` restringida a los rangos CIDR declarados en `var.redes_juego`.
- **`gke.tf`**: Clúster GKE zonal (`nebula-${terraform.workspace}`), pool de nodos `game-pool` con autoescalado (`min_node_count` a `max_node_count`, etiquetado con `rol = "juego"` y tag `game-server`) y repositorio Docker `nebula` en Artifact Registry.
- **`agones.tf`**: Despliegue declarativo con `helm_release` de **Agones** (`v1.44.0`, en `agones-system` con `serviceMonitor` habilitado) y **`kube-prometheus-stack`** (Prometheus + Grafana en `monitoring` con lectura de `PodMonitor` y `ServiceMonitor` en todo el clúster).
- **`clasificacion.tf`**: Base de datos Firestore opcional (`google_firestore_database.scores`) y servicio Cloud Run v2 `nebula-leaderboard-${terraform.workspace}` con identidad dedicada y escalado de `0` a `max_instance_count`.
- **Perfiles por entorno/cuota**:
  - [`completo.tfvars.example`](completo.tfvars.example): Modo completo del PDF (3 a 12 nodos `e2-standard-4`, para 1 000 jugadores y 500 espectadores).
  - [`reducido.tfvars.example`](reducido.tfvars.example): Modo reducido por cuota del PDF (1 a 3 nodos `e2-standard-4`, para 300 jugadores y 200 espectadores).

## 1. Validación local sin credenciales ni estado remoto

En Windows con Terraform instalado:

```powershell
cd infra
terraform fmt -check
terraform init -backend=false
terraform validate
```

O mediante Docker Desktop si el binario `terraform` no está instalado en el host:

```powershell
docker run --rm -v "${PWD}/infra:/workspace" -w /workspace hashicorp/terraform:1.9 fmt -check
docker run --rm -v "${PWD}/infra:/workspace" -w /workspace hashicorp/terraform:1.9 init -backend=false
docker run --rm -v "${PWD}/infra:/workspace" -w /workspace hashicorp/terraform:1.9 validate
```

La evidencia de validación local se encuentra en [`../evidencia/terraform-init-local.txt`](../evidencia/terraform-init-local.txt) y [`../evidencia/terraform-validate.txt`](../evidencia/terraform-validate.txt).

## 2. Preparar estado remoto y plan revisable (requiere autorización de nube)

Antes de ejecutar cualquier cambio en GCP:
1. Confirma el proyecto, región (`us-central1`), presupuesto y alertas de Cloud Billing (p. ej. alerta de USD 10 con umbrales en 50 %, 90 % y 100 %).
2. Crea el bucket de estado remoto con versionado:
   ```powershell
   gcloud storage buckets create gs://nebula-tfstate-<TU-ID> --location=us-central1 --uniform-bucket-level-access
   gcloud storage buckets update gs://nebula-tfstate-<TU-ID> --versioning
   ```
3. Copia `completo.tfvars.example` o `reducido.tfvars.example` a `lab.tfvars` y genera el plan revisable sin aplicar cambios:
   ```powershell
   .\preparar-plan.ps1 -Proyecto "<TU-PROYECTO>" -BucketEstado "nebula-tfstate-<TU-ID>" -ArchivoVars "lab.tfvars"
   ```
4. Revisa [`../evidencia/terraform-plan-revisable.txt`](../evidencia/terraform-plan-revisable.txt) antes de ejecutar `terraform apply nebula.tfplan`.

## 3. Destrucción y verificación de inventario post-pruebas

Al concluir la sesión de pruebas, destruye la infraestructura y verifica que no queden recursos huérfanos cobrando (clústeres GKE, VMs como `locust-gen`, balanceadores/forwarding rules, IPs estáticas o discos):

```powershell
.\verificar-limpieza.ps1 -Proyecto "<TU-PROYECTO>" -ArchivoVars "lab.tfvars" -EjecutarDestroy
```
