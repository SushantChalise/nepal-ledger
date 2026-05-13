<#
.SYNOPSIS
  Scaffold a new ADR with the next available number.

.EXAMPLE
  .\scripts\new-adr.ps1 "Cloudflare R2 archival policy"
#>

param(
  [Parameter(Mandatory=$true, Position=0)]
  [string]$Title
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$adrDir = Join-Path $repoRoot 'docs\decisions'

if (-not (Test-Path $adrDir)) { New-Item -ItemType Directory -Path $adrDir | Out-Null }

# Find next ADR number
$existing = Get-ChildItem $adrDir -Filter '*.md' | ForEach-Object {
  if ($_.Name -match '^(\d{4})-') { [int]$Matches[1] }
} | Sort-Object -Descending | Select-Object -First 1

$next = if ($null -eq $existing) { 1 } else { $existing + 1 }
$num = '{0:D4}' -f $next
$slug = ($Title -replace '[^\w\s-]', '' -replace '\s+', '-').ToLower()
$file = Join-Path $adrDir "$num-$slug.md"

$today = Get-Date -Format 'yyyy-MM-dd'

$template = @"
# ADR-$num`: $Title

- **Status:** Proposed
- **Date:** $today
- **Deciders:** Mother Opus
- **Tags:** TBD

## Context

<What is the problem? What forces are at play? What constraints?>

## Decision

<What did we decide? One paragraph.>

## Alternatives Considered

- **Option A:** description. Why rejected.
- **Option B (chosen):** description.

## Consequences

### Positive
-

### Negative
-

### Neutral / unknown
-

## References

- Strategy plan section:
- Related ADRs:
- External docs:
"@

Set-Content -Path $file -Value $template -Encoding utf8
Write-Host "Created: $file" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit the ADR and fill in Context + Alternatives"
Write-Host "  2. Discuss with user if escalation criteria met"
Write-Host "  3. Mark Status: Accepted and fill Decision + Consequences"
Write-Host "  4. git commit -m 'docs(adr): add ADR-$num $Title'"
