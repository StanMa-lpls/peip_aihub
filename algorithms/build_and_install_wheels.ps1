#! /usr/bin/env pwsh
#! powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\build_and_install_wheels.ps1" -Python "C:\tools\miniconda3\envs\peip_aihub\python.exe"

param(
    [string]$CondaEnv = "peip_aihub",
    [string]$Python = "",
    [string[]]$Projects = @(),
    [switch]$NoInstall,
    [switch]$SkipBuildUpgrade
)

$ErrorActionPreference = "Stop"

$AlgorithmsRoot = Resolve-Path $PSScriptRoot
$PeipRoot = Resolve-Path (Join-Path $AlgorithmsRoot "..")
$WheelDir = Join-Path $PeipRoot "wheels"

function Invoke-TargetPython {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    if ($Python.Trim()) {
        & $Python @Arguments
        return
    }

    & conda run -n $CondaEnv python @Arguments
}

function Get-ProjectRoots {
    if ($Projects.Count -gt 0) {
        foreach ($Project in $Projects) {
            $ProjectPath = Resolve-Path (Join-Path $AlgorithmsRoot $Project)
            if (-not (Test-Path (Join-Path $ProjectPath "pyproject.toml"))) {
                throw "pyproject.toml not found under project: $ProjectPath"
            }
            $ProjectPath
        }
        return
    }

    Get-ChildItem -Path $AlgorithmsRoot -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "pyproject.toml") } |
        Sort-Object @{ Expression = { if ($_.Name -eq "algorithms") { 0 } else { 1 } } }, Name |
        ForEach-Object { $_.FullName }
}

function Remove-BuildArtifacts {
    param([string]$ProjectRoot)

    Remove-Item -Recurse -Force `
        (Join-Path $ProjectRoot "dist"), `
        (Join-Path $ProjectRoot "build") `
        -ErrorAction SilentlyContinue

    Get-ChildItem -Path (Join-Path $ProjectRoot "src") -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force $WheelDir | Out-Null
$ExistingWheels = Get-ChildItem -Path $WheelDir -Filter "*.whl" -File -ErrorAction SilentlyContinue
if ($ExistingWheels.Count -gt 0) {
    Write-Host "Removing existing wheels from: $WheelDir"
    $ExistingWheels | Remove-Item -Force
}

Write-Host "Algorithms root: $AlgorithmsRoot"
Write-Host "peip_aihub root:  $PeipRoot"
Write-Host "Wheel output:     $WheelDir"
if ($Python.Trim()) {
    Write-Host "Python target:    $Python"
} else {
    Write-Host "Conda env target: $CondaEnv"
}

if (-not $SkipBuildUpgrade) {
    Write-Host "Ensuring build package is available..."
    Invoke-TargetPython -m pip install --upgrade build
}

$BuiltWheels = @()

foreach ($ProjectRoot in Get-ProjectRoots) {
    $ProjectName = Split-Path $ProjectRoot -Leaf
    $DistDir = Join-Path $ProjectRoot "dist"

    Write-Host ""
    Write-Host "=== Building $ProjectName ==="
    Remove-BuildArtifacts $ProjectRoot

    Invoke-TargetPython -m build $ProjectRoot --wheel

    $Wheel = Get-ChildItem -Path $DistDir -Filter "*.whl" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $Wheel) {
        throw "No wheel produced under: $DistDir"
    }

    $TargetWheel = Join-Path $WheelDir $Wheel.Name
    Copy-Item -Force $Wheel.FullName $TargetWheel
    $BuiltWheels += $TargetWheel

    Write-Host "Wheel copied:"
    Write-Host "  $TargetWheel"
}

Write-Host ""
Write-Host "Completed wheels:"
foreach ($Wheel in $BuiltWheels) {
    Write-Host "  $Wheel"
}

if (-not $NoInstall) {
    Write-Host ""
    Write-Host "Installing completed wheels..."
    Invoke-TargetPython -m pip install --force-reinstall --find-links $WheelDir @BuiltWheels
} else {
    Write-Host "Wheel installation skipped because -NoInstall was provided."
}
