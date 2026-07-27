$tmp = "lambda/package"
$prj = (Get-Item .).FullName
Write-Host "Limpiando directorio temporal..."
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
Write-Host "Instalando dependencias (pip install -t $tmp)..."
pip install -r "lambda/requirements.txt" -t $tmp 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: pip install fallo"; exit 1 }
Write-Host "Copiando fuentes a $tmp..."
Copy-Item -Path "lambda/src/*.py" -Destination $tmp
Write-Host "Creando lambda_package.zip con zipfile de Python..."
python -c @"
import zipfile, os
srcdir = r'$prj\lambda\package'
dst = r'$prj\lambda_package.zip'
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(srcdir):
        for f in files:
            p = os.path.join(root, f)
            zf.write(p, os.path.relpath(p, srcdir))
"@
Remove-Item -Recurse -Force $tmp
Write-Host "OK: lambda_package.zip creado en raiz del proyecto"
