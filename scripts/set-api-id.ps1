$path = Join-Path -Path (Get-Location).Path -ChildPath "frontend/.api_id"
if (Test-Path -LiteralPath $path) {
    $id = Get-Content -Path $path -Raw
    if ($id) {
        [Environment]::SetEnvironmentVariable('API_ID', $id.Trim(), 'User')
        Write-Host "API_ID=$($id.Trim())"
    }
}