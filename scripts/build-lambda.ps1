$tmp = "lambda/package"
$prj = (Get-Item .).FullName
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$pipOutput = pip install --ignore-installed -r "lambda/requirements.txt" -t $tmp 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host $pipOutput; Write-Host "pip install fallo"; exit 1 }
Copy-Item -Path "lambda/src/*.py" -Destination $tmp
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
