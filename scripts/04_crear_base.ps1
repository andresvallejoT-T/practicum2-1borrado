. "$PSScriptRoot\comun.ps1"
Require-PythonProyecto
Push-Location $Proyecto
try { Invoke-Paso $PythonProyecto @('local.py','iniciar') }
finally { Pop-Location }
