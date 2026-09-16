param([string[]]$Tables, [string]$Build = '1.60.1.69876', [string]$Folder = 'db2')
$ErrorActionPreference = 'Stop'
$target = Join-Path $PSScriptRoot (Join-Path '..\evidence\2026-09-16' $Folder)
[void](New-Item -ItemType Directory -Path $target -Force)
$Tables | ForEach-Object -Parallel {
    $ProgressPreference = 'SilentlyContinue'
    $table = $_
    $path = Join-Path $using:target ($table + '.csv')
    $url = 'https://wago.tools/db2/' + $table + '/csv?build=' + $using:Build
    if (Test-Path -LiteralPath $path) { Write-Output "$table cached"; return }
    try {
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 80
        if ($response.Headers['Content-Type'] -notmatch 'text/csv') { throw 'Response is not CSV' }
        [System.IO.File]::WriteAllText($path, [string]$response.Content, [System.Text.UTF8Encoding]::new($false))
        Write-Output "$table OK $((Get-Item -LiteralPath $path).Length) bytes"
    } catch { Write-Output "$table ERROR $($_.Exception.Message)" }
} -ThrottleLimit 4
