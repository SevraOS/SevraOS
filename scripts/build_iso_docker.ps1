$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path "$ScriptDir\.."
$OutDir = Join-Path $RepoRoot "sevraos\out"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

docker run --rm --privileged `
    -v "${RepoRoot}:/build:ro" `
    -v "${OutDir}:/out" `
    archlinux:latest `
    bash /build/scripts/build_iso_docker.sh
