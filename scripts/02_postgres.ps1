. "$PSScriptRoot\comun.ps1"
$LocalProyecto = Join-Path $Proyecto '.local'
$PgCtl = Join-Path $LocalProyecto 'pgsql\bin\pg_ctl.exe'
if (Test-Path -LiteralPath $PgCtl) {
    Invoke-Paso $PgCtl @('--version')
    Write-Host 'PostgreSQL local ya existe; no se reemplazaran binarios ni datos.'
    return
}
if (Test-Path -LiteralPath (Join-Path $LocalProyecto 'pgdata\PG_VERSION')) {
    throw 'Hay un cluster sin binarios. Restaura binarios compatibles antes de continuar.'
}
New-Item -ItemType Directory -Force -Path $LocalProyecto | Out-Null
$Zip = Join-Path $LocalProyecto 'postgresql.zip'
$HashEsperado = '520c8c6f19abb3b31fa83ec5e486e2f769eedd7593d94e60a7cda8a5bfb4df91'
if (-not (Test-Path -LiteralPath $Zip)) {
    Invoke-Paso 'curl.exe' @('-fL','--retry','2','-o',$Zip,'https://get.enterprisedb.com/postgresql/postgresql-17.12-2-windows-x64-binaries.zip')
}
if ((Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash -ne $HashEsperado) {
    throw 'Checksum incorrecto. Revisa la descarga; no se extraera ni ejecutara.'
}
Invoke-Paso 'tar.exe' @('-xf',$Zip,'-C',$LocalProyecto,'pgsql/bin','pgsql/lib','pgsql/share')
if (-not (Test-Path -LiteralPath $PgCtl)) { throw 'No se encontro pg_ctl tras extraer' }
Invoke-Paso $PgCtl @('--version')
