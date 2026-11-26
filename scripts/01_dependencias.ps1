. "$PSScriptRoot\comun.ps1"
Push-Location $Proyecto
try {
    if (-not (Test-Path -LiteralPath $PythonProyecto)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            Invoke-Paso 'py' @('-3.11','-m','venv','.venv')
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            Invoke-Paso 'python' @('-m','venv','.venv')
        } else { throw 'Instala Python 3.11 de 64 bits y vuelve a abrir PowerShell.' }
    }
    Invoke-Paso $PythonProyecto @('-c','import sys,struct; assert sys.version_info >= (3,11) and struct.calcsize(''P'')==8, ''Se requiere Python >=3.11 de 64 bits''')
    Invoke-Paso $PythonProyecto @('-m','pip','install','-r','requirements.txt')
    Invoke-Paso $PythonProyecto @('-m','pip','check')
} finally { Pop-Location }
