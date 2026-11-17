param(
    [Parameter(Mandatory = $true)]
    [string]$Proyecto,
    [Parameter(Mandatory = $true)]
    [string]$BucketEstado,
    [string]$PrefijoEstado = "nebula/dev",
    [Parameter(Mandatory = $true)]
    [string]$ArchivoVars,
    [string]$SalidaTexto = "..\evidencia\terraform-plan-revisable.txt"
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    Write-Host "1. Inicializando estado remoto GCS con bloqueo en gs://$BucketEstado/$PrefijoEstado ..."
    terraform init -reconfigure `
        -backend-config="bucket=$BucketEstado" `
        -backend-config="prefix=$PrefijoEstado"

    Write-Host "2. Validando sintaxis y tipos..."
    terraform validate

    Write-Host "3. Generando plan binario (nebula.tfplan) y versión de texto revisable ($SalidaTexto)..."
    terraform plan -var-file="$ArchivoVars" -var="proyecto=$Proyecto" -out="nebula.tfplan"
    terraform show -no-color "nebula.tfplan" | Out-File -FilePath $SalidaTexto -Encoding utf8
    Write-Host "Plan generado en $SalidaTexto. Revisa costos y recursos antes de ejecutar 'terraform apply nebula.tfplan'."
}
finally {
    Pop-Location
}
