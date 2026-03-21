param(
    [Parameter(Mandatory = $true)]
    [string]$ApiKey,

    [Parameter(Mandatory = $true)]
    [string]$EndpointId,

    [Parameter(Mandatory = $true)]
    [string]$AudioPath,

    [string]$ImagePath,

    [string]$OutputDir = ".\test_outputs",

    [ValidateSet("full", "crop", "resize", "extcrop", "extfull")]
    [string]$Preprocess = "full",

    [int]$PoseStyle = 0,

    [double]$ExpressionScale = 1.0,

    [ValidateSet(256, 512)]
    [int]$Size = 256,

    [bool]$StillMode = $true,

    [ValidateSet("none", "gfpgan", "RestoreFormer")]
    [string]$Enhancer = "none",

    [switch]$ReturnVideoBase64,

    [int]$PollSeconds = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $AudioPath)) {
    throw "Audio file not found: $AudioPath"
}

if ($ImagePath -and -not (Test-Path $ImagePath)) {
    throw "Image file not found: $ImagePath"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$audioBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path $AudioPath)))
$bodyInput = @{
    audio_base64 = $audioBase64
    options = @{
        preprocess = $Preprocess
        pose_style = $PoseStyle
        expression_scale = $ExpressionScale
        size = $Size
        still_mode = $StillMode
        enhancer = $(if ($Enhancer -eq "none") { $null } else { $Enhancer })
    }
    return_video_base64 = [bool]$ReturnVideoBase64
}

if ($ImagePath) {
    $imageBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path $ImagePath)))
    $bodyInput["source_image_base64"] = $imageBase64
}

$body = @{ input = $bodyInput } | ConvertTo-Json -Depth 10

Write-Host "Submitting job to endpoint $EndpointId ..."
$job = Invoke-RestMethod `
    -Method Post `
    -Uri "https://api.runpod.ai/v2/$EndpointId/run" `
    -Headers @{ Authorization = "Bearer $ApiKey" } `
    -ContentType "application/json" `
    -Body $body

$jobId = $job.id
Write-Host "Job submitted: $jobId"

do {
    Start-Sleep -Seconds $PollSeconds
    $status = Invoke-RestMethod `
        -Method Get `
        -Uri "https://api.runpod.ai/v2/$EndpointId/status/$jobId" `
        -Headers @{ Authorization = "Bearer $ApiKey" }

    Write-Host "Status: $($status.status)"
} while ($status.status -eq "IN_QUEUE" -or $status.status -eq "IN_PROGRESS")

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$statusPath = Join-Path $OutputDir "status_$timestamp.json"
$status | ConvertTo-Json -Depth 20 | Set-Content -Path $statusPath
Write-Host "Saved full status JSON to $statusPath"

if ($status.status -ne "COMPLETED") {
    throw "Job failed. Inspect $statusPath"
}

if ($status.output.status -eq "error") {
    Write-Host "Worker returned an error:"
    Write-Host ($status.output | ConvertTo-Json -Depth 10)
    exit 1
}

if ($ReturnVideoBase64 -and $status.output.video_base64) {
    $videoPath = Join-Path $OutputDir "result_$timestamp.mp4"
    [IO.File]::WriteAllBytes($videoPath, [Convert]::FromBase64String($status.output.video_base64))
    Write-Host "Saved video to $videoPath"
}
else {
    Write-Host "No video bytes requested. Inspect output JSON/logs in $statusPath"
}
