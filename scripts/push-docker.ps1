#Requires -Version 5.1
<#
  构建并推送到你的 Docker 仓库（需已 docker login）。

  Docker Hub 示例：
    .\scripts\push-docker.ps1 -DockerUser "你的DockerHub用户名"

  仅私有仓库地址（不含镜像名）：
    .\scripts\push-docker.ps1 -Registry "registry.cn-hangzhou.aliyuncs.com/命名空间"

  指定标签：
    .\scripts\push-docker.ps1 -DockerUser "你的用户名" -Tag "v1.0.0"
#>
param(
    [string] $DockerUser = "",
    [string] $Registry = "",
    [string] $Tag = "latest"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$prefix = $null
if ($Registry) {
    $prefix = $Registry.Trim().TrimEnd("/")
}
elseif ($DockerUser) {
    $prefix = $DockerUser.Trim()
}
if (-not $prefix) {
    Write-Error "请提供 -DockerUser（Docker Hub 用户名）或 -Registry（完整仓库前缀，如 registry.example.com/ns）"
}

$env:BACKEND_IMAGE = "${prefix}/campus-supply-backend:${Tag}"
$env:FRONTEND_IMAGE = "${prefix}/campus-supply-frontend:${Tag}"

Write-Host "镜像将推送为:" -ForegroundColor Cyan
Write-Host "  $($env:BACKEND_IMAGE)"
Write-Host "  $($env:FRONTEND_IMAGE)"
Write-Host ""
Write-Host "若尚未登录，请先执行: docker login [仓库地址]" -ForegroundColor Yellow
Write-Host ""

docker compose build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose push
exit $LASTEXITCODE
