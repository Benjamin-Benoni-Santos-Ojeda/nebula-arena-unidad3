param(
    [Parameter(Mandatory = $true)]
    [string]$Proyecto,
    [Parameter(Mandatory = $true)]
    [string]$ArchivoVars,
    [switch]$EjecutarDestroy,
    [string]$SalidaInventario = "..\evidencia\inventario-post-destroy.txt"
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    if ($EjecutarDestroy) {
        Write-Host "Ejecutando terraform destroy para el proyecto $Proyecto..."
        terraform destroy -var-file="$ArchivoVars" -var="proyecto=$Proyecto" -auto-approve
    }

    Write-Host "Verificando inventario de recursos en GCP para descartar recursos huérfanos..."
    $lineas = @()
    $lineas += "=== Auditoría de recursos post-destroy ($(Get-Date -Format o)) ==="
    $lineas += "Proyecto: $Proyecto"
    $lineas += ""
    $lineas += "--- Terraform state list ---"
    $line_tf = terraform state list 2>&1
    $lineas += $line_tf

    if (Get-Command gcloud -ErrorAction SilentlyContinue) {
        $lineas += "--- GKE Clusters ---"
        $lineas += (gcloud container clusters list --project=$Proyecto --format="table(name,location,status,currentNodeCount)" 2>&1)
        $lineas += "--- Compute Engine Instances (VMs) ---"
        $lineas += (gcloud compute instances list --project=$Proyecto --format="table(name,zone,machineType,status)" 2>&1)
        $lineas += "--- Forwarding Rules / Load Balancers ---"
        $lineas += (gcloud compute forwarding-rules list --project=$Proyecto --format="table(name,region,IPAddress,target)" 2>&1)
        $lineas += "--- Static Addresses (IPs) ---"
        $lineas += (gcloud compute addresses list --project=$Proyecto --format="table(name,region,address,status)" 2>&1)
        $lineas += "--- Persistent Disks ---"
        $lineas += (gcloud compute disks list --project=$Proyecto --format="table(name,zone,sizeGb,status)" 2>&1)
        $lineas += "--- Cloud Run Services ---"
        $lineas += (gcloud run services list --project=$Proyecto --format="table(SERVICE,REGION,URL)" 2>&1)
        $lineas += "--- Artifact Registry Repositories ---"
        $lineas += (gcloud artifacts repositories list --project=$Proyecto --format="table(name,format,location)" 2>&1)
    } else {
        $lineas += "gcloud CLI no instalado en este host; ejecuta este script donde tengas gcloud autenticado."
    }

    $lineas | Out-File -FilePath $SalidaInventario -Encoding utf8
    Get-Content $SalidaInventario
}
finally {
    Pop-Location
}
