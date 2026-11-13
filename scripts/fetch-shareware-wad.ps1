# Baixa o DOOM shareware IWAD (v1.8) e grava como ./wad/doom1.wad
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$WadDir = Join-Path $Root "wad"
$GzPath = Join-Path $WadDir "doom1v18.wad.gz"
$OutWad = Join-Path $WadDir "doom1.wad"

# Mirror público ibiblio (shareware redistribuível)
$Url = "http://www.ibiblio.org/pub/linux/games/doom/doom1v18.wad.gz"

New-Item -ItemType Directory -Force -Path $WadDir | Out-Null

if (Test-Path $OutWad) {
    $len = (Get-Item $OutWad).Length
    if ($len -gt 1000000) {
        Write-Host "Já existe: $OutWad ($len bytes)"
        exit 0
    }
    Remove-Item -Force $OutWad
}

Write-Host "Baixando $Url ..."
& curl.exe -fsSL -o $GzPath $Url
if ($LASTEXITCODE -ne 0) { throw "curl falhou ao baixar o IWAD" }

# Descompacta gzip
$in = [System.IO.File]::OpenRead($GzPath)
try {
    $gz = New-Object System.IO.Compression.GZipStream($in, [System.IO.Compression.CompressionMode]::Decompress)
    $out = [System.IO.File]::Create($OutWad)
    try {
        $gz.CopyTo($out)
    } finally {
        $out.Close()
        $gz.Close()
    }
} finally {
    $in.Close()
}

Remove-Item -Force $GzPath
$len = (Get-Item $OutWad).Length
if ($len -lt 1000000) { throw "doom1.wad inválido ($len bytes)" }
Write-Host "OK: $OutWad ($len bytes)"
