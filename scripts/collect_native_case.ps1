param(
  [Parameter(Mandatory=$true)][string]$RunDir,
  [Parameter(Mandatory=$true)][string]$InputFile,
  [Parameter(Mandatory=$true)][string]$ArtifactRoot,
  [string]$CaseTitle = "Native File Evidence Case",
  [string]$Scenario = "a native extractor file-level run"
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runPath = (Resolve-Path (Join-Path $root $RunDir)).Path
$artifactPath = [System.IO.Path]::GetFullPath((Join-Path $root $ArtifactRoot))

if (-not $artifactPath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "ArtifactRoot must stay inside project root: $artifactPath"
}

function Write-Utf8NoBom {
  param([string]$Path, [string]$Value)
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Value, $encoding)
}

if (Test-Path $artifactPath) {
  Remove-Item -LiteralPath $artifactPath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $artifactPath | Out-Null

foreach ($fileName in @("result.json", "trace.json", "summary.md")) {
  $source = Join-Path $runPath $fileName
  if (Test-Path $source) {
    Copy-Item -LiteralPath $source -Destination (Join-Path $artifactPath $fileName) -Force
  }
}

foreach ($dirName in @("office", "html", "retrieval")) {
  $source = Join-Path $runPath $dirName
  if (Test-Path $source) {
    Copy-Item -LiteralPath $source -Destination (Join-Path $artifactPath $dirName) -Recurse -Force
  }
}

$inputCopied = $false
$resolvedInput = [System.IO.Path]::GetFullPath((Join-Path $root $InputFile))
if (Test-Path $resolvedInput) {
  $extension = [IO.Path]::GetExtension($resolvedInput)
  Copy-Item -LiteralPath $resolvedInput -Destination (Join-Path $artifactPath ("input" + $extension)) -Force
  $inputCopied = $true
}

$qualityStatus = "not available"
$qualityScore = "not available"
$retrievalStatus = if (Test-Path (Join-Path $artifactPath "retrieval\retrieval_chunks.jsonl")) { "included" } else { "not included" }
$resultPath = Join-Path $artifactPath "result.json"
if (Test-Path $resultPath) {
  $result = Get-Content -Raw -Encoding UTF8 -LiteralPath $resultPath | ConvertFrom-Json
  if ($result.quality) {
    $qualityStatus = [string]$result.quality.status
    $qualityScore = [string]$result.quality.score
  }
}

$readme = @(
  "# $CaseTitle",
  "",
  "This directory preserves $Scenario.",
  "",
  "- Source run: $RunDir",
  "- Input copied: $inputCopied",
  "- Original input path: $InputFile",
  "- Quality: $qualityStatus ($qualityScore/100)",
  "- Retrieval export: $retrievalStatus",
  "- Evidence files: result.json, trace.json, summary.md, native parser artifacts, retrieval/",
  ""
) -join "`n"
Write-Utf8NoBom -Path (Join-Path $artifactPath "README.md") -Value $readme

$indexDir = Split-Path $artifactPath -Parent
New-Item -ItemType Directory -Force -Path $indexDir | Out-Null
$rows = @()
Get-ChildItem -LiteralPath $indexDir -Directory | Sort-Object Name | ForEach-Object {
  $caseDir = $_
  $caseName = $caseDir.Name
  $caseQuality = "not available"
  $caseScore = "not available"
  $caseSource = "not available"
  $caseInputCopied = [bool](Get-ChildItem -LiteralPath $caseDir.FullName -Filter "input.*" -File -ErrorAction SilentlyContinue)
  $caseRetrieval = if (Test-Path (Join-Path $caseDir.FullName "retrieval\retrieval_chunks.jsonl")) { "included" } else { "not included" }
  $caseResultPath = Join-Path $caseDir.FullName "result.json"
  if (Test-Path $caseResultPath) {
    $caseResult = Get-Content -Raw -Encoding UTF8 -LiteralPath $caseResultPath | ConvertFrom-Json
    if ($caseResult.quality) {
      $caseQuality = [string]$caseResult.quality.status
      $caseScore = [string]$caseResult.quality.score
    }
    if ($caseResult.extracted.content_summary.source_counts) {
      $caseSource = (($caseResult.extracted.content_summary.source_counts.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ", ")
    }
  }
  $rows += "| $caseName | $caseSource | $caseQuality ($caseScore/100) | $caseInputCopied | $caseRetrieval |"
}

$index = @(
  "# Native File Case Artifacts",
  "",
  "Collected by scripts/collect_native_case.ps1.",
  "",
  "| Case | Source counts | Quality | Input copied | Retrieval |",
  "| --- | --- | --- | --- | --- |"
)
$index += $rows
$index += @("")
$index = $index -join "`n"
Write-Utf8NoBom -Path (Join-Path $indexDir "README.md") -Value $index

Write-Output "Collected native case artifacts at $ArtifactRoot"
