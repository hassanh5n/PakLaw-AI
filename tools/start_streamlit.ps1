param(
    [int]$Port = 8501
)

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$app = Join-Path $root 'app.py'

Start-Process -FilePath 'python' -ArgumentList @('-m', 'streamlit', 'run', $app, '--server.port', $Port.ToString(), '--server.address', '0.0.0.0', '--server.headless', 'true') -WorkingDirectory $root -WindowStyle Hidden
Write-Host "Streamlit launch requested on http://localhost:$Port"
