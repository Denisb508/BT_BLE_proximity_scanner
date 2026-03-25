param(
    [string]$PythonExe = "C:\Program Files\PyManager\python.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Join-Path $root "app"
$portablePython = Join-Path $root "python"
$wheelDir = Join-Path $root "wheels"
$logsDir = Join-Path $appRoot "logs"

New-Item -ItemType Directory -Force -Path $wheelDir | Out-Null
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

if (!(Test-Path $PythonExe)) {
    throw "Python not found at: $PythonExe"
}

Write-Host "Using Python: $PythonExe"
& $PythonExe --version
& $PythonExe -c "import tkinter; print('tkinter OK')"

$pythonHome = & $PythonExe -c "import sys; print(sys.base_prefix)"
$pythonHome = $pythonHome.Trim()

if (!(Test-Path $pythonHome)) {
    throw "Could not resolve Python base_prefix folder: $pythonHome"
}

Write-Host "Python home: $pythonHome"
Write-Host "Downloading offline wheels..."
& $PythonExe -m pip download --only-binary=:all: --dest $wheelDir bleak==0.21.1 typing-extensions
if ($LASTEXITCODE -ne 0) { throw "pip download failed" }

if (Test-Path $portablePython) {
    Remove-Item $portablePython -Recurse -Force
}

Write-Host "Copying full Python runtime..."
Copy-Item $pythonHome $portablePython -Recurse -Force

Write-Host "Installing bleak into bundled Python..."
& (Join-Path $portablePython "python.exe") -m pip install --no-index --find-links $wheelDir bleak==0.21.1
if ($LASTEXITCODE -ne 0) { throw "offline pip install failed" }

$cmd = @"
@echo off
cd /d %~dp0
start "" "python\pythonw.exe" "app\ble_gui_proximity_offline.py"
"@
Set-Content -Path (Join-Path $root "START_BLE.cmd") -Value $cmd -Encoding ASCII

$cmd2 = @"
@echo off
cd /d %~dp0
python\python.exe "app\ble_gui_proximity_offline.py"
pause
"@
Set-Content -Path (Join-Path $root "DEBUG_BLE.cmd") -Value $cmd2 -Encoding ASCII

$vbs = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\python\pythonw.exe" & Chr(34) & " " & Chr(34) & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\app\ble_gui_proximity_offline.py" & Chr(34), 0, False
"@
Set-Content -Path (Join-Path $root "START_BLE_SILENT.vbs") -Value $vbs -Encoding ASCII

Write-Host ""
Write-Host "DONE"
Write-Host "Portable bundle prepared in: $root"
Write-Host "Copy the whole folder to offline PC."
Write-Host "On offline PC: double click START_BLE.cmd or START_BLE_SILENT.vbs"
