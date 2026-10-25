param([ValidateSet('pcb','schematic')][string]$Editor = 'pcb', [string]$KiCadBin = 'C:\Program Files\KiCad\10.0\bin', [switch]$Ipc)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$runtimeRoot = Join-Path $repoRoot '.runtime'
$configRoot = Join-Path $runtimeRoot 'config'
if ($Ipc) {
    $configRoot = Join-Path $runtimeRoot 'ipc-config'
    $ipcVersionRoot = Join-Path $configRoot '10.0'
    New-Item -ItemType Directory -Force $ipcVersionRoot | Out-Null
    if (-not (Test-Path (Join-Path $ipcVersionRoot 'kicad_common.json'))) {
        Get-ChildItem -LiteralPath (Join-Path $runtimeRoot 'config\10.0') -File | Copy-Item -Destination $ipcVersionRoot
    }
    $settingsPath = Join-Path $ipcVersionRoot 'kicad_common.json'
    $settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
    $settings.api.enable_server = $true
    [IO.File]::WriteAllText($settingsPath, ($settings | ConvertTo-Json -Depth 40), (New-Object Text.UTF8Encoding $false))
    & (Join-Path $KiCadBin 'python.exe') (Join-Path $PSScriptRoot 'prepare_ipc_probe.py')
}
$documentsRoot = Join-Path $runtimeRoot 'documents'
$env:KICAD_CONFIG_HOME = $configRoot
$env:KICAD_DOCUMENTS_HOME = $documentsRoot
$env:KOA_PROBE_LOG = Join-Path $runtimeRoot 'probe-events.jsonl'
$pluginDirectory = Join-Path $configRoot '10.0\scripting\plugins'
New-Item -ItemType Directory -Force $documentsRoot | Out-Null
if (-not $Ipc) {
    New-Item -ItemType Directory -Force $pluginDirectory | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot 'prototype\open_assistant_probe.py') -Destination (Join-Path $pluginDirectory 'open_assistant_probe.py')
}
$executable = if ($Editor -eq 'pcb') { 'pcbnew.exe' } else { 'eeschema.exe' }
# Visible launch is intentional: the user requested real editor UI verification.
Start-Process -FilePath (Join-Path $KiCadBin $executable) -WindowStyle Normal -PassThru | Select-Object Id, ProcessName
