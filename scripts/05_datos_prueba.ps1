. "$PSScriptRoot\comun.ps1"
Require-PythonProyecto
Push-Location $Proyecto
try { Invoke-Paso $PythonProyecto @('local.py','verificar') }
finally { Pop-Location }
