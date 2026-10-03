param(
    [string]$ToolsRoot = (Join-Path $PSScriptRoot '..\..\..\work\toolchains'),
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'

function Show-Checkpoint([string]$Message) {
    Write-Host "`n$Message" -ForegroundColor Cyan
    [void](Read-Host 'Save the terminal screenshot, then press Enter to continue')
}

Write-Host 'Lab1: actual terminal verification (no upload)' -ForegroundColor Cyan
Write-Host 'Save screenshots under ../report/images/ using the names below.'
Write-Host 'Stage 1: build and run. QEMU stays in the kernel loop after printing.'
Write-Host 'When the kernel message appears, press Ctrl+A, release, then X to quit QEMU.'
& (Join-Path $PSScriptRoot 'run-lab.ps1') -Action build -ToolsRoot $ToolsRoot -Python $Python -Rebuild
Show-Checkpoint 'Save terminal-build.png. Include the build command and successful output.'
Clear-Host
Write-Host 'Actual make qemu. Press Ctrl+A, release, then X after the startup message.'
& (Join-Path $PSScriptRoot 'run-lab.ps1') -Action run -ToolsRoot $ToolsRoot -Python $Python
Show-Checkpoint 'Save terminal-qemu.png. Include the command, OpenSBI and kernel startup message.'

Clear-Host
Write-Host 'Stage 2: real QEMU/GDB local checks (this is not the official grader).'
& (Join-Path $PSScriptRoot 'run-lab.ps1') -Action check -ToolsRoot $ToolsRoot -Python $Python
Show-Checkpoint 'Save terminal-check.png. Include all PASS lines and the 13-check summary.'

Clear-Host
Write-Host 'Stage 3: official make grade attempt. Missing grade.sh is an incomplete official check.'
$gccBin = Join-Path $ToolsRoot 'gcc\xpack-riscv-none-elf-gcc-11.3.0-1\bin'
$makeBin = Join-Path $ToolsRoot 'make\xpack-windows-build-tools-4.4.1-3\bin'
$qemuBin = Join-Path $ToolsRoot 'qemu'
$originalPath = $env:Path
$env:Path = "$gccBin;$makeBin;$qemuBin;C:\Program Files\Git\usr\bin;$originalPath"
Push-Location $PSScriptRoot
try {
    & (Join-Path $makeBin 'make.exe') 'GCCPREFIX=riscv-none-elf-' 'QEMU=qemu-system-riscv64' "PYTHON=$Python" grade
    $gradeExit = $LASTEXITCODE
    Write-Host "Official make grade exit code: $gradeExit"
    Show-Checkpoint 'Save terminal-grade.png. Preserve the real result, including errors if any.'
}
finally {
    Pop-Location
    $env:Path = $originalPath
}
# The supplied grade target cleans the build before trying the missing script.
& (Join-Path $PSScriptRoot 'run-lab.ps1') -Action build -ToolsRoot $ToolsRoot -Python $Python
Write-Host 'Review complete. Screenshots still need to be checked and referenced in the report.'
