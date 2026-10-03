param(
    [ValidateSet('build', 'run', 'debug', 'gdb', 'check')]
    [string]$Action = 'check',
    [string]$ToolsRoot = (Join-Path $PSScriptRoot '..\..\..\work\toolchains'),
    [string]$Python = 'python',
    [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'
$gccBin = Join-Path $ToolsRoot 'gcc\xpack-riscv-none-elf-gcc-11.3.0-1\bin'
$makeBin = Join-Path $ToolsRoot 'make\xpack-windows-build-tools-4.4.1-3\bin'
$qemuBin = Join-Path $ToolsRoot 'qemu'
foreach ($tool in @((Join-Path $gccBin 'riscv-none-elf-gcc.exe'),
                    (Join-Path $makeBin 'make.exe'),
                    (Join-Path $qemuBin 'qemu-system-riscv64.exe'))) {
    if (-not (Test-Path -LiteralPath $tool)) {
        throw "Missing tool: $tool. See README.md or pass -ToolsRoot."
    }
}
$originalPath = $env:Path
$env:Path = "$gccBin;$makeBin;$qemuBin;C:\Program Files\Git\usr\bin;$originalPath"
Push-Location $PSScriptRoot
try {
    $makeArgs = @('GCCPREFIX=riscv-none-elf-', 'QEMU=qemu-system-riscv64', "PYTHON=$Python")
    if ($Rebuild) { $makeArgs += '-B' }
    switch ($Action) {
        'build' { }
        'run' { $makeArgs += 'qemu' }
        default { $makeArgs += $Action }
    }
    & (Join-Path $makeBin 'make.exe') @makeArgs
    if ($LASTEXITCODE -ne 0) { throw "make failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
    $env:Path = $originalPath
}
