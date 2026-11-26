param([switch]$ConDemo, [switch]$SinPgAdmin)
. "$PSScriptRoot\comun.ps1"
& "$PSScriptRoot\01_dependencias.ps1"
& "$PSScriptRoot\02_postgres.ps1"
& "$PSScriptRoot\04_crear_base.ps1"
if (-not $SinPgAdmin) { & "$PSScriptRoot\03_pgadmin.ps1" }
if ($ConDemo) { & "$PSScriptRoot\05_datos_prueba.ps1" }
Write-Host 'Preparacion completada. Abre el acceso Abrir base de datos o ejecuta local.py web.'
