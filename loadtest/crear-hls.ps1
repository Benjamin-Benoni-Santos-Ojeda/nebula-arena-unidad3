param(
    [Parameter(Mandatory = $true)]
    [string]$Salida
)

$ErrorActionPreference = "Stop"
$directorio = Join-Path $Salida "live/nebula"
New-Item -ItemType Directory -Path $directorio -Force | Out-Null
$directorio = (Resolve-Path -LiteralPath $directorio).Path

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    $argumentos = @(
        "-hide_banner", "-nostdin", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30",
        "-t", "60", "-c:v", "libx264", "-preset", "veryfast",
        "-b:v", "800k", "-minrate", "800k", "-maxrate", "800k",
        "-bufsize", "1600k", "-x264-params", "nal-hrd=cbr",
        "-g", "60", "-sc_threshold", "0",
        "-f", "hls", "-hls_time", "2", "-hls_playlist_type", "vod",
        "-hls_segment_filename", (Join-Path $directorio "segmento-%03d.ts"),
        (Join-Path $directorio "360p.m3u8")
    )
    & ffmpeg @argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "FFmpeg no pudo generar el manifiesto HLS."
    }
} else {
    Write-Host "FFmpeg no encontrado en PATH; generando flujo HLS CBR sintético (30 segmentos de 2 s a 800 kbps = 200 KB/segmento)..."
    # 800 kbps durante 2 s = 1 600 000 bits = 200 000 bytes (1064 paquetes MPEG-TS de 188 bytes)
    $paquetes = 1064
    $buffer = New-Object byte[] ($paquetes * 188)
    for ($p = 0; $p -lt $paquetes; $p++) {
        $offset = $p * 188
        $buffer[$offset] = 0x47 # Sync byte MPEG-TS
        $buffer[$offset + 1] = 0x1F
        $buffer[$offset + 2] = 0xFF # Null packet PID 0x1FFF
        $buffer[$offset + 3] = 0x10
    }
    $lineas = @(
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:2",
        "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD"
    )
    for ($i = 0; $i -lt 30; $i++) {
        $nombre = ("segmento-{0:D3}.ts" -f $i)
        $rutaSeg = Join-Path $directorio $nombre
        [System.IO.File]::WriteAllBytes($rutaSeg, $buffer)
        $lineas += "#EXTINF:2.000000,"
        $lineas += $nombre
    }
    $lineas += "#EXT-X-ENDLIST"
    $rutaM3u8 = Join-Path $directorio "360p.m3u8"
    [System.IO.File]::WriteAllLines($rutaM3u8, $lineas, [System.Text.UTF8Encoding]::new($false))
}
