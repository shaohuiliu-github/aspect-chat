param([switch]$Stop)
$ErrorActionPreference = 'Stop'
# Windows PowerShell 5 treats native stderr differently from PowerShell 7.
function Invoke-DockerNative {
    param([string[]]$Arguments)
    $savedPreference=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        $output=@(& docker @Arguments 2>&1)
        $code=$LASTEXITCODE
    } finally { $ErrorActionPreference=$savedPreference }
    return [PSCustomObject]@{Output=$output;Code=$code}
}
function Test-LocalPort {
    param([int]$Port)
    $socket=New-Object System.Net.Sockets.TcpClient
    try {
        $connect=$socket.BeginConnect('127.0.0.1',$Port,$null,$null)
        if (-not $connect.AsyncWaitHandle.WaitOne(250)) {return $false}
        $socket.EndConnect($connect)
        return $true
    } catch {return $false} finally {$socket.Dispose()}
}
Set-Location $PSScriptRoot
$workspace = Join-Path $PSScriptRoot 'workspace'
New-Item -ItemType Directory -Force -Path $workspace,(Join-Path $workspace 'inputs'),(Join-Path $workspace '.host-open') | Out-Null
$hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($PSScriptRoot))
$name = 'aspect-chat-' + ([BitConverter]::ToString($hash).Replace('-','').Substring(0,12).ToLower())
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install and start Docker Desktop: https://docs.docker.com/get-started/get-docker/' }
$info=Invoke-DockerNative -Arguments @('info','--format','{{.Architecture}}')
if ($info.Code -ne 0) { throw 'Start Docker Desktop first (Linux containers mode).' }
$arch=($info.Output -join '').Trim()
$exists=(Invoke-DockerNative -Arguments @('container','inspect',$name)).Code -eq 0
if ($Stop) {
    if ($exists) {
        $result=Invoke-DockerNative -Arguments @('stop','-t','30',$name)
        if ($result.Code -ne 0) {throw ($result.Output -join "`n")}
    }
    Write-Host 'Stopped. Models and results remain in workspace.'; exit 0
}
switch ($arch) { 'aarch64' {$arch='arm64'} 'arm64' {$arch='arm64'} 'x86_64' {$arch='amd64'} 'amd64' {$arch='amd64'} default {throw "Unsupported architecture: $arch"} }
$image = "aspect-chat:2.0.3-aspect3.1.0-$arch"
if ((Invoke-DockerNative -Arguments @('image','inspect',$image)).Code -ne 0) {
    $archive = Join-Path $PSScriptRoot "images/aspect-chat-$arch.tar.gz"
    if (Test-Path $archive) {
        Write-Host 'Importing the environment for first launch...'
        $result=Invoke-DockerNative -Arguments @('load','--input',$archive)
    } elseif (Test-Path 'image-reference.txt') {
        $remote=(Get-Content 'image-reference.txt' -Raw).Trim()
        if ($remote -notmatch '^[a-z0-9][a-z0-9./_:@-]+$') {throw 'Invalid registry image reference.'}
        Write-Host 'Downloading the environment from the registry for first launch...'
        $result=Invoke-DockerNative -Arguments @('pull',$remote)
        if ($result.Code -eq 0) {
            $result.Output | Write-Host
            $result=Invoke-DockerNative -Arguments @('tag',$remote,$image)
        }
    } elseif (Test-Path 'source/packaging/Dockerfile') {
        Write-Host 'Building online (about 2 GB download)...'
        $result=Invoke-DockerNative -Arguments @('build','-f','source/packaging/Dockerfile','-t',$image,'source')
    } else {throw "Missing image for $arch. Use the matching release package."}
    $result.Output | Write-Host
    if ($result.Code -ne 0) {throw 'Image import or build failed.'}
}
if ($exists) {
    $running=(Invoke-DockerNative -Arguments @('inspect','--format','{{.State.Running}}',$name)).Output -join ''
    if ($running -ne 'true') {
        $result=Invoke-DockerNative -Arguments @('start',$name)
        if ($result.Code -ne 0) {throw ($result.Output -join "`n")}
    }
    $port=[int]((Invoke-DockerNative -Arguments @('inspect','--format','{{index .Config.Labels "aspect-chat.port"}}',$name)).Output -join '')
} else {
    $port = 8517
    if ($env:ASPECT_CHAT_PORT) { $port = [int]$env:ASPECT_CHAT_PORT }
    $launched = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        if (Test-LocalPort -Port $port) {$port++;continue}
        $runArgs=@('run','-d','--name',$name,'--restart','unless-stopped','--stop-timeout','30',
            '--label',"aspect-chat.port=$port",'--label','aspect-chat.package=2.0.3',
            '-p',"127.0.0.1:${port}:8517",'--mount',"type=bind,source=$workspace,target=/workspace",
            '-e',"ASPECT_CHAT_HOST_WORKSPACE=$workspace",'-e',"ASPECT_CHAT_PUBLIC_PORT=$port",'-e',"ASPECT_CHAT_INSTANCE=$name",$image)
        $result=Invoke-DockerNative -Arguments $runArgs
        $result.Output | Set-Content (Join-Path $workspace 'container-start.log')
        if ($result.Code -eq 0) { $launched=$true; break }
        $state=(Invoke-DockerNative -Arguments @('inspect','--format','{{.State.Status}}',$name)).Output -join ''
        if ($state -eq 'created') { $null=Invoke-DockerNative -Arguments @('rm',$name) }
        if (($result.Output -join ' ') -match 'address already in use|port is already allocated') {$port++} else {throw ($result.Output -join "`n")}
    }
    if (-not $launched) {throw 'No free port found.'}
}
$url = "http://127.0.0.1:$port"
$ready=$false
for ($attempt=0; $attempt -lt 90; $attempt++) {
    try { $health=Invoke-RestMethod "$url/api/health" -TimeoutSec 2; if ($health.app -eq 'aspect-chat' -and $health.instance -eq $name) {$ready=$true;break} } catch {}
    Start-Sleep -Seconds 1
}
if (-not $ready) { (Invoke-DockerNative -Arguments @('logs','--tail','80',$name)).Output | Write-Host; throw 'Application did not start.' }
Write-Host "chatGFD: $url"
Write-Host "Models and results: $workspace"
Write-Host 'Keep this window open for the Open Folder buttons. Closing it leaves calculations running.'
if ($env:ASPECT_CHAT_NO_BROWSER -ne '1') { Start-Process $url }
while ($true) {
    @{time=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000;platform='win32'} | ConvertTo-Json -Compress | Set-Content (Join-Path $workspace '.host-open/bridge.json')
    $state=Invoke-DockerNative -Arguments @('inspect','--format','{{.State.Running}}',$name)
    if ($state.Code -ne 0 -or ($state.Output -join '') -ne 'true') {break}
    Get-ChildItem (Join-Path $workspace '.host-open') -Filter '*.request' | ForEach-Object {
        $requestFile=$_.FullName
        $opened=$false
        $value=(Get-Content $_.FullName -Raw).Trim()
        if ($value -match '^(case|job):([a-f0-9]{12})$') {
            $relative=if ($Matches[1] -eq 'case') {"cases/$($Matches[2])"} else {$(
                $identifier=$Matches[2]
                $run=Get-ChildItem (Join-Path $workspace 'runs') -Directory | Where-Object {
                    $manifest=Join-Path $_.FullName 'manifest.json'
                    if (Test-Path $manifest) { try { (Get-Content $manifest -Raw | ConvertFrom-Json).job_id -eq $identifier } catch {$false} }
                } | Select-Object -First 1
                if ($run) {"runs/$($run.Name)/output"} else {"runs/$identifier/output"}
            )}
            $target=Join-Path $workspace $relative
            $safe=$true; $current=Get-Item $target -ErrorAction SilentlyContinue
            while ($current -and $current.FullName.Length -ge $workspace.Length) {
                if ($current.Attributes -band [IO.FileAttributes]::ReparsePoint) {$safe=$false;break}
                $current=$current.Parent
            }
            if ($safe -and (Test-Path $target -PathType Container)) { Start-Process explorer.exe -ArgumentList ('"'+$target+'"');$opened=$true }
        }
        @{state=$(if ($opened) {'opened'} else {'failed'});time=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000} | ConvertTo-Json -Compress | Set-Content ([IO.Path]::ChangeExtension($requestFile,'.response'))
        Remove-Item $requestFile
    }
    Start-Sleep -Seconds 1
}
