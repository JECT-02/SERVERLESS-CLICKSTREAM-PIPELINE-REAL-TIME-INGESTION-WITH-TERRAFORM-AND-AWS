try {
  $r = Invoke-WebRequest -Uri "http://localhost:4566/health" -UseBasicParsing -TimeoutSec 5
  if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 }
} catch {
  Write-Host "Floci no esta corriendo. Ejecuta: make floci-up"
  exit 1
}
