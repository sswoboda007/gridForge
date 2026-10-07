param(
    [switch]$SkipInstall,
    [int]$CoverageFailUnder = 90
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $RepoRoot

try {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

    function Invoke-CiStep {
        param(
            [string]$Name,
            [string[]]$Command
        )

        Write-Host "==> $Name"
        & $Command[0] $Command[1..($Command.Length - 1)]
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE"
        }
    }

    if (-not $SkipInstall) {
        Invoke-CiStep "Install development dependencies" @("python", "-m", "pip", "install", "-e", ".[dev]")
    }

    Invoke-CiStep "Ruff format check" @("python", "-m", "ruff", "format", "--check", ".")
    Invoke-CiStep "Ruff lint" @("python", "-m", "ruff", "check", ".")
    Invoke-CiStep "Mypy type check" @("python", "-m", "mypy", "gridforge", "tests", "main.py", "flaskApp.py")
    Invoke-CiStep "Pytest with coverage" @(
        "python",
        "-m",
        "pytest",
        "-p",
        "pytest_cov",
        "--cov=gridforge",
        "--cov-report=term-missing",
        "--cov-fail-under=$CoverageFailUnder",
        "tests"
    )

    Write-Host "Local CI checks passed."
} finally {
    Pop-Location
}
