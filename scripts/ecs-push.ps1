param(
    [string]$EndpointUrl = "http://localhost:4566",
    [string]$LocalRegistry = "localhost:5100",
    [string]$LocalImage = "clickstream-inference:latest"
)

$ErrorActionPreference = "Stop"

$awsEndpoint = [Environment]::GetEnvironmentVariable('AWS_ENDPOINT_URL')

if ([string]::IsNullOrEmpty($awsEndpoint) -or $awsEndpoint -match 'localhost|4566') {
    Write-Host "Local Floci detected - pushing to $LocalRegistry..."

    $loginPassword = aws ecr get-login-password --endpoint-url $EndpointUrl 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host 'ECR get-login-password failed'; exit 1 }

    $loginPassword | docker login --username AWS --password-stdin $LocalRegistry 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host 'Docker login failed'; exit 1 }

    $tag = "${LocalRegistry}/clickstream-inference:latest"
    docker tag $LocalImage $tag 2>&1
    docker push $tag 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host 'Docker push failed'; exit 1 }

    Write-Host 'Push to local ECR complete'
    exit 0
}

$awsAccount = "000000000000"
$awsRegion = "us-east-1"
$awsRegistry = "${awsAccount}.dkr.ecr.${awsRegion}.amazonaws.com"

Write-Host "Pushing to AWS ECR ($awsRegistry)..."
aws ecr get-login-password --region $awsRegion | docker login --username AWS --password-stdin $awsRegistry
if ($LASTEXITCODE -ne 0) { Write-Host 'AWS ECR login failed'; exit 1 }
docker tag $LocalImage "${awsRegistry}/clickstream-inference:latest"
docker push "${awsRegistry}/clickstream-inference:latest"
if ($LASTEXITCODE -ne 0) { Write-Host 'AWS ECR push failed'; exit 1 }