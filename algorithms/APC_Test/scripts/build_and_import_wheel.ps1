param(
    [string]$Python = "python",
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PeipRoot = Resolve-Path (Join-Path $ProjectRoot "..\..")
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"
$EggInfoDir = Join-Path $ProjectRoot "src\apc_engine.egg-info"
$WheelDir = Join-Path $PeipRoot "wheels"
$WheelName = "apc_engine-0.1.0-py3-none-any.whl"
$BuiltWheel = Join-Path $DistDir $WheelName
$TargetWheel = Join-Path $WheelDir $WheelName

Write-Host "APC_Test root: $ProjectRoot"
Write-Host "peip_aihub root: $PeipRoot"

Write-Host "Cleaning previous build artifacts..."
Remove-Item -Recurse -Force $DistDir, $BuildDir, $EggInfoDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $WheelDir | Out-Null

Write-Host "Ensuring build package is available..."
& $Python -m pip install --upgrade build

Write-Host "Building wheel..."
& $Python -m build $ProjectRoot --wheel

if (-not (Test-Path $BuiltWheel)) {
    throw "Expected wheel not found: $BuiltWheel"
}

Write-Host "Copying wheel to peip_aihub wheels directory..."
Copy-Item -Force $BuiltWheel $TargetWheel

Write-Host "Wheel copied:"
Write-Host "  $TargetWheel"

if (-not $NoInstall) {
    Write-Host "Installing wheel into current Python environment..."
    & $Python -m pip install --force-reinstall $TargetWheel
} else {
    Write-Host "Skipping wheel installation because -NoInstall was provided."
}

Write-Host "Done."
