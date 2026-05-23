param(
  [string]$Output = "dist\mineru-data-agent-submission.zip",
  [switch]$IncludeReviewExchange
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dist = Join-Path $root "dist"
$stage = Join-Path $dist "_submission_stage"
if ($IncludeReviewExchange -and $Output -eq "dist\mineru-data-agent-submission.zip") {
  $Output = "dist\mineru-data-agent-review.zip"
}
$outputPath = Join-Path $root $Output
New-Item -ItemType Directory -Force -Path $dist | Out-Null
if (Test-Path $outputPath) {
  Remove-Item -LiteralPath $outputPath -Force
}
if (Test-Path $stage) {
  Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null

$items = @(
  "README.md",
  "CONTRIBUTING.md",
  "LICENSE",
  ".gitignore",
  ".gitattributes",
  ".github",
  "pyproject.toml",
  "src",
  "docs",
  "examples",
  "scripts",
  "submission_artifacts",
  "tests"
)
if ($IncludeReviewExchange) {
  $items += "review_exchange"
}

$excludeDirs = @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "runs", "dist")
$excludeFiles = @("*.pyc", "*.pyo", "*.log", ".env")

foreach ($item in $items) {
  $source = Join-Path $root $item
  $target = Join-Path $stage $item
  if (Test-Path $source -PathType Leaf) {
    Copy-Item -LiteralPath $source -Destination $target -Force
  } elseif (Test-Path $source -PathType Container) {
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Get-ChildItem -LiteralPath $source -Recurse -Force | ForEach-Object {
      $relative = $_.FullName.Substring($source.Length).TrimStart("\", "/")
      if (-not $relative) { return }
      $parts = $relative -split '[\\/]'
      if ($parts | Where-Object { $excludeDirs -contains $_ }) { return }
      if (-not $_.PSIsContainer) {
        foreach ($pattern in $excludeFiles) {
          if ($_.Name -like $pattern) { return }
        }
      }
      $dest = Join-Path $target $relative
      if ($_.PSIsContainer) {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
      } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
      }
    }
  }
}

$textExtensions = @(".md", ".json", ".jsonl", ".txt", ".py", ".toml", ".ps1", ".html")
$pathReplacements = @(
  @{ Pattern = [regex]::Escape($root); Replacement = "<PROJECT_ROOT>" },
  @{ Pattern = "(?i)[A-Z]:\\data_agent\\MinerU"; Replacement = "<MINERU_ROOT>" },
  @{ Pattern = "(?i)<USER_HOME>"; Replacement = "<USER_HOME>" }
)
Get-ChildItem -LiteralPath $stage -Recurse -File | Where-Object {
  $textExtensions -contains $_.Extension.ToLowerInvariant()
} | ForEach-Object {
  $text = [System.IO.File]::ReadAllText($_.FullName)
  $clean = $text
  foreach ($replacement in $pathReplacements) {
    $clean = [regex]::Replace($clean, $replacement.Pattern, $replacement.Replacement)
  }
  if ($clean -ne $text) {
    [System.IO.File]::WriteAllText($_.FullName, $clean, [System.Text.UTF8Encoding]::new($false))
  }
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($outputPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
  Get-ChildItem -LiteralPath $stage -Recurse -File | ForEach-Object {
    $entryName = $_.FullName.Substring($stage.Length).TrimStart("\", "/") -replace '\\', '/'
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entryName) | Out-Null
  }
} finally {
  $zip.Dispose()
}
Remove-Item -LiteralPath $stage -Recurse -Force
Write-Output "Created $Output"
