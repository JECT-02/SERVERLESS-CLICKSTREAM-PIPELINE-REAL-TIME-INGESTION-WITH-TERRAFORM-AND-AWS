param(
    [string]$TerraformDir = "infra/environments/local",
    [string]$BucketName = "clickstream-bucket",
    [string]$EndpointUrl = "http://localhost:4566"
)

$ErrorActionPreference = "Continue"

Push-Location $TerraformDir

Write-Host "Empty S3 bucket"
try {
    $objects = aws s3 ls "s3://$BucketName" --endpoint-url $EndpointUrl --recursive --summarize 2>&1 | Select-String "Total Objects" | ForEach-Object { $_ -replace '\D', '' }
    if ($objects -and $objects -gt 0) {
        aws s3 rm "s3://$BucketName" --recursive --endpoint-url $EndpointUrl 2>&1 | Out-Null
        Write-Host "S3 bucket emptied"
    } else {
        Write-Host "S3 bucket empty or not found"
    }
} catch {
    Write-Host "S3 bucket not found or already removed"
}

Write-Host "Remove stale resources from state"
$staleResources = @(
    "module.api_gateway.aws_api_gateway_integration_response.options",
    "module.api_gateway.aws_api_gateway_method_response.options"
)
foreach ($res in $staleResources) {
    $check = terraform state list 2>&1 | Select-String $res
    if ($check) {
        terraform state rm $res 2>&1 | Out-Null
        Write-Host "Removed stale: $res"
    }
}

Write-Host "Terraform destroy"
$env:TF_IN_AUTOMATION = "true"
terraform destroy -auto-approve 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "Terraform destroy failed with exit code $exitCode. Cleaning state files"
    $stateFiles = Get-ChildItem -Path "." -Filter "terraform.tfstate*" -ErrorAction SilentlyContinue
    foreach ($f in $stateFiles) {
        Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
        Write-Host "Deleted: $($f.Name)"
    }
}

Write-Host "Destroy complete"

Pop-Location
exit $exitCode
