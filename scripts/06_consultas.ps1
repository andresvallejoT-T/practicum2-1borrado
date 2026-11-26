param([ValidateSet('revision','diagnostico')][string]$Tipo = 'revision')
. "$PSScriptRoot\comun.ps1"
Require-PythonProyecto
Push-Location $Proyecto
$AnteriorPassword = $env:PGPASSWORD
$AnteriorEncoding = $env:PGCLIENTENCODING
try {
    Invoke-Paso $PythonProyecto @('local.py','iniciar')
    $Conexion = Get-Content -LiteralPath '.local\conexion.json' -Raw | ConvertFrom-Json
    $env:PGPASSWORD = $Conexion.password
    $env:PGCLIENTENCODING = 'UTF8'
    $Nombre = if ($Tipo -eq 'revision') { '03_consultas_relacionales.sql' } else { '02_consultas_verificacion.sql' }
    $Sql = Join-Path $PSScriptRoot ('sql\' + $Nombre)
    Invoke-Paso (Join-Path $Proyecto '.local\pgsql\bin\psql.exe') @(
        '-X','-h','127.0.0.1','-p',([string]$Conexion.port),'-U','opendata','-d','opendata',
        '-v','ON_ERROR_STOP=1','-P','pager=off','-f',$Sql)
} finally {
    $env:PGPASSWORD = $AnteriorPassword
    $env:PGCLIENTENCODING = $AnteriorEncoding
    Pop-Location
}
