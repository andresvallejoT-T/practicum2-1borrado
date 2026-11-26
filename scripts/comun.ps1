$ErrorActionPreference = 'Stop'
$Proyecto = Split-Path -Parent $PSScriptRoot
$PythonProyecto = Join-Path $Proyecto '.venv\Scripts\python.exe'
function Invoke-Paso {
    param([string]$Programa, [string[]]$Argumentos)
    & $Programa @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Fallo ejecutando $Programa (codigo $LASTEXITCODE)" }
}
function Require-PythonProyecto {
    if (-not (Test-Path -LiteralPath $PythonProyecto)) { throw 'Ejecuta primero 01_dependencias.ps1' }
}
