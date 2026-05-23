param(
  [string]$RunDir = "runs\mineru_cli_refresh\4568109b3cc5",
  [string]$InputFile = "<MINERU_ROOT>\demo\pdfs\small_ocr.pdf",
  [string]$ArtifactRoot = "submission_artifacts\mineru_cases\case_mineru_cli_low_quality_pdf",
  [string]$CaseTitle = "MinerU CLI Evidence Case",
  [string]$Scenario = "a real MinerU CLI run for a low-quality scanned PDF scenario"
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runPath = (Resolve-Path (Join-Path $root $RunDir)).Path
$artifactPath = [System.IO.Path]::GetFullPath((Join-Path $root $ArtifactRoot))

if (-not $artifactPath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "ArtifactRoot must stay inside project root: $artifactPath"
}

function Write-Utf8NoBom {
  param(
    [string]$Path,
    [string]$Value
  )
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

foreach ($dirName in @("mineru", "retrieval", "kb")) {
  $source = Join-Path $runPath $dirName
  if (Test-Path $source) {
    Copy-Item -LiteralPath $source -Destination (Join-Path $artifactPath $dirName) -Recurse -Force
  }
}

$inputCopied = $false
if (Test-Path $InputFile) {
  $extension = [IO.Path]::GetExtension($InputFile)
  Copy-Item -LiteralPath $InputFile -Destination (Join-Path $artifactPath ("input" + $extension)) -Force
  $inputCopied = $true
}

$toolName = "not available"
$toolStatus = "not available"
$elapsedSeconds = "not available"
$qualityStatus = "not available"
$qualityScore = "not available"
$retrievalStatus = "not included in this run"

$tracePath = Join-Path $runPath "trace.json"
if (Test-Path $tracePath) {
  $trace = Get-Content -Raw -Encoding UTF8 -LiteralPath $tracePath | ConvertFrom-Json
  if (@($trace.tool_calls).Count -gt 0) {
    $toolName = [string]$trace.tool_calls[0].tool
    $toolStatus = [string]$trace.tool_calls[0].status
    $elapsedSeconds = [string]$trace.tool_calls[0].elapsed_seconds
  }
}

$resultPath = Join-Path $runPath "result.json"
if (Test-Path $resultPath) {
  $result = Get-Content -Raw -Encoding UTF8 -LiteralPath $resultPath | ConvertFrom-Json
  if ($result.quality) {
    $qualityStatus = [string]$result.quality.status
    $qualityScore = [string]$result.quality.score
  }
  if ($result.retrieval_export -or (Test-Path (Join-Path $runPath "retrieval"))) {
    $retrievalStatus = "included"
  }
}

$note = if ($retrievalStatus -eq "included") {
  "This case includes the current post-processing evidence: structured result, trace, summary, MinerU artifacts, and retrieval export."
} else {
  "Note: this case was collected from a run without retrieval export. Re-run the agent with the same PDF and collect the latest run to refresh this evidence."
}

$readme = @(
  "# $CaseTitle",
  "",
  "This directory preserves $Scenario.",
  "",
  "- Source run: $RunDir",
  "- Input copied: $inputCopied",
  "- Original input path: $InputFile",
  "- Tool: $toolName",
  "- Tool status: $toolStatus",
  "- Tool elapsed seconds: $elapsedSeconds",
  "- Quality: $qualityStatus ($qualityScore/100)",
  "- Retrieval export: $retrievalStatus",
  "- Evidence files: result.json, trace.json, summary.md, mineru/",
  "",
  $note
) -join "`n"
Write-Utf8NoBom -Path (Join-Path $artifactPath "README.md") -Value $readme

$indexDir = Split-Path $artifactPath -Parent
New-Item -ItemType Directory -Force -Path $indexDir | Out-Null
$rows = @()
Get-ChildItem -LiteralPath $indexDir -Directory | Sort-Object Name | ForEach-Object {
  $caseDir = $_
  $caseName = $caseDir.Name
  $caseTool = "not available"
  $caseStatus = "not available"
  $caseElapsed = "not available"
  $caseQuality = "not available"
  $caseScore = "not available"
  $caseInputCopied = [bool](Get-ChildItem -LiteralPath $caseDir.FullName -Filter "input.*" -File -ErrorAction SilentlyContinue)
  $caseRetrieval = if (Test-Path (Join-Path $caseDir.FullName "retrieval\retrieval_chunks.jsonl")) { "included" } else { "not included" }

  $caseTracePath = Join-Path $caseDir.FullName "trace.json"
  if (Test-Path $caseTracePath) {
    $caseTrace = Get-Content -Raw -Encoding UTF8 -LiteralPath $caseTracePath | ConvertFrom-Json
    if (@($caseTrace.tool_calls).Count -gt 0) {
      $caseTool = [string]$caseTrace.tool_calls[0].tool
      $caseStatus = [string]$caseTrace.tool_calls[0].status
      $caseElapsed = [string]$caseTrace.tool_calls[0].elapsed_seconds
    }
  }

  $caseResultPath = Join-Path $caseDir.FullName "result.json"
  if (Test-Path $caseResultPath) {
    $caseResult = Get-Content -Raw -Encoding UTF8 -LiteralPath $caseResultPath | ConvertFrom-Json
    if ($caseResult.quality) {
      $caseQuality = [string]$caseResult.quality.status
      $caseScore = [string]$caseResult.quality.score
    }
  }
  $rows += "| $caseName | $caseTool | $caseStatus | $caseElapsed | $caseQuality ($caseScore/100) | $caseInputCopied | $caseRetrieval |"
}

$index = @(
  "# MinerU Case Artifacts",
  "",
  "Collected by scripts/collect_mineru_case.ps1.",
  "",
  "| Case | Tool | Status | Elapsed seconds | Quality | Input copied | Retrieval |",
  "| --- | --- | --- | ---: | --- | --- | --- |"
)
$index += $rows
$index += @(
  ""
)
$index = $index -join "`n"
Write-Utf8NoBom -Path (Join-Path $indexDir "README.md") -Value $index

Write-Output "Collected MinerU case artifacts at $ArtifactRoot"
