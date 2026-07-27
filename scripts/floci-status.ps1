try {
  $r = Invoke-WebRequest -Uri "http://localhost:4566/health" -UseBasicParsing
  $r.Content
} catch {
  Write-Host "Floci no responde"
}
