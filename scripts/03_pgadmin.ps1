. "$PSScriptRoot\comun.ps1"
Require-PythonProyecto
$Candidatos = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\pgAdmin 4'),
    (Join-Path $env:ProgramFiles 'pgAdmin 4')
)
$PgAdmin = $Candidatos | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'runtime\pgAdmin4.exe') } | Select-Object -First 1
if (-not $PgAdmin) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Instala pgAdmin desde pgadmin.org y repite este script.' }
    Invoke-Paso 'winget' @('install','--id','PostgreSQL.pgAdmin','--exact','--source','winget','--silent','--accept-source-agreements','--accept-package-agreements')
    $PgAdmin = $Candidatos | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'runtime\pgAdmin4.exe') } | Select-Object -First 1
}
if (-not $PgAdmin) { throw 'No se encontro pgAdmin en las rutas habituales.' }
if (Get-Process pgAdmin4 -ErrorAction SilentlyContinue) {
    throw 'Cierra pgAdmin y repite 03_pgadmin.ps1 para importar la conexion sin conflictos.'
}
Push-Location $Proyecto
$AnteriorPath = $env:PATH
try {
    Invoke-Paso $PythonProyecto @('local.py','iniciar')
    $env:PATH = (Join-Path $PgAdmin 'runtime') + ';' + $env:PATH
    $PgPython = Join-Path $PgAdmin 'python\python.exe'
    $Setup = Join-Path $PgAdmin 'web\setup.py'
    $Db = Join-Path $env:APPDATA 'pgAdmin\pgadmin4.db'
    if (-not (Test-Path -LiteralPath $Db)) { Invoke-Paso $PgPython @($Setup,'setup-db') }
    if (-not (Test-Path -LiteralPath $Db)) { throw 'pgAdmin no creo su configuracion en la ruta esperada.' }
    $Conexion = Get-Content -LiteralPath '.local\conexion.json' -Raw | ConvertFrom-Json
    $Passfile = Join-Path $Proyecto '.local\pgadmin.pgpass'
    [IO.File]::WriteAllText($Passfile, "127.0.0.1:$($Conexion.port):*:opendata:$($Conexion.password)" + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    $Exportado = Join-Path $Proyecto '.local\pgadmin-existentes.json'
    Invoke-Paso $PgPython @($Setup,'dump-servers',$Exportado,'--sqlite-path',$Db)
    if (-not (Test-Path -LiteralPath $Exportado)) { throw 'No se pudo inspeccionar la configuracion de pgAdmin.' }
    $Existentes = Get-Content -LiteralPath $Exportado -Raw | ConvertFrom-Json
    $Coincide = @($Existentes.Servers.PSObject.Properties | Where-Object {
        $_.Value.Host -eq '127.0.0.1' -and $_.Value.Port -eq $Conexion.port -and
        $_.Value.Username -eq 'opendata' -and $_.Value.MaintenanceDB -eq 'opendata'
    })
    if ($Coincide.Count -eq 0) {
        $Servidores = @{ Servers = @{ '1' = @{
            Name = 'OpenData local'; Group = 'Practicum'; Host = '127.0.0.1';
            Port = $Conexion.port; Username = 'opendata'; MaintenanceDB = 'opendata';
            SSLMode = 'prefer'; DBRestriction = 'opendata';
            ConnectionParameters = @{ sslmode = 'prefer'; connect_timeout = 10; passfile = $Passfile }
        } } }
        $Importar = Join-Path $Proyecto '.local\pgadmin-servidores.json'
        [IO.File]::WriteAllText($Importar, ($Servidores | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
        Invoke-Paso $PgPython @($Setup,'load-servers',$Importar,'--sqlite-path',$Db)
        Invoke-Paso $PgPython @($Setup,'dump-servers',$Exportado,'--sqlite-path',$Db)
        $Registrados = Get-Content -LiteralPath $Exportado -Raw | ConvertFrom-Json
        $Verificados = @($Registrados.Servers.PSObject.Properties | Where-Object {
            $_.Value.Host -eq '127.0.0.1' -and $_.Value.Port -eq $Conexion.port -and
            $_.Value.Username -eq 'opendata' -and $_.Value.MaintenanceDB -eq 'opendata'
        })
        if ($Verificados.Count -eq 0) { throw 'La conexion no aparece en pgAdmin tras importarla.' }
    } else { Write-Host 'La conexion ya existe: se conserva sin reemplazarla.' }
    $Shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $Proyecto 'Abrir base de datos.lnk'))
    $Shortcut.TargetPath = Join-Path $Proyecto '.venv\Scripts\pythonw.exe'
    $Shortcut.Arguments = '"' + (Join-Path $Proyecto 'abrir_pgadmin.pyw') + '"'
    $Shortcut.WorkingDirectory = $Proyecto
    $Shortcut.IconLocation = Join-Path $PgAdmin 'pgAdmin4.ico'
    $Shortcut.Save()
    Write-Host 'pgAdmin configurado. Abre el acceso Abrir base de datos.'
} finally {
    $env:PATH = $AnteriorPath
    Pop-Location
}
