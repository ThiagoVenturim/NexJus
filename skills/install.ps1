# Instala as skills e agentes do NexJus no Claude Code sem precisar de pip.
# Uso: .\skills\install.ps1 [install|uninstall|validate|list] [--project DIR | --target DIR] [--force] [--dry-run]
# Sem argumentos instala em $HOME\.claude. Requer Python 3.11 ou mais novo.
$ErrorActionPreference = 'Stop'

$python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
$argumentos = @($args)
if ($argumentos.Count -eq 0) { $argumentos = @('install') }
$anterior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $PSScriptRoot 'src') + $(if ($anterior) { [IO.Path]::PathSeparator + $anterior } else { '' })
    & $python -m nexjus_skills @argumentos
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $anterior
}
