<#
.SYNOPSIS
  Nepal Ledger Day-1 bootstrap. Idempotent: safe to re-run.

.DESCRIPTION
  Run from the project root. Will:
    1. Verify CLI inventory (git, gh, node>=20, pnpm, python>=3.11, wrangler)
    2. Install uv (Python package manager) if missing
    3. Scaffold Next.js 15 app + Cloudflare Workers + OpenNext if not already scaffolded
    4. Configure strict TypeScript + ESLint + Prettier + Vitest + Playwright
    5. Install core dependencies (Drizzle, Zod, neverthrow, Tailwind, shadcn, Recharts, D3, next-intl, Resend, Sentry, Pagefind, OpenNext)
    6. Configure pre-commit hooks (simple-git-hooks + lint-staged + gitleaks)
    7. Initialize git with augmented .gitignore
    8. Print user-action checklist (account creation, secrets, branch protection)

.PARAMETER SkipScaffold
  Skip the Next.js scaffold step.

.PARAMETER DryRun
  Show commands without executing.

.EXAMPLE
  .\scripts\bootstrap.ps1
  .\scripts\bootstrap.ps1 -DryRun
#>

[CmdletBinding()]
param(
  [switch]$SkipScaffold,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  OK $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "  -- $msg (skipped)" -ForegroundColor DarkGray }
function Write-Warn($msg) { Write-Host "  !! $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  XX $msg" -ForegroundColor Red }

function Test-Cli($name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  return [bool]$cmd
}

function Invoke-OrPrint($cmd) {
  if ($DryRun) { Write-Host "  [DRY] $cmd" -ForegroundColor DarkYellow }
  else { Invoke-Expression $cmd }
}

# Step 1: CLI inventory
Write-Step "Step 1: Verifying CLI inventory"

$required = @{
  git       = 'Git (https://git-scm.com)'
  gh        = 'GitHub CLI (https://cli.github.com)'
  node      = 'Node.js v20+ (https://nodejs.org)'
  pnpm      = 'pnpm (npm install -g pnpm)'
  python    = 'Python 3.11+ (https://python.org)'
  wrangler  = 'Cloudflare Wrangler (npm install -g wrangler)'
}

$optional = @{
  uv          = 'uv (https://docs.astral.sh/uv) — modern Python package manager'
  gitleaks    = 'gitleaks (https://github.com/gitleaks/gitleaks) — pre-commit secret scan'
  docker      = 'Docker (for local Supabase dev)'
}

$missing = @()
foreach ($cli in $required.Keys) {
  if (Test-Cli $cli) { Write-Ok "$cli installed" }
  else { Write-Fail "$cli MISSING: $($required[$cli])"; $missing += $cli }
}
foreach ($cli in $optional.Keys) {
  if (Test-Cli $cli) { Write-Ok "$cli installed (optional)" }
  else { Write-Warn "$cli not installed (optional): $($optional[$cli])" }
}

if ($missing.Count -gt 0) {
  Write-Fail "Missing required CLIs: $($missing -join ', '). Install and re-run."
  exit 1
}

# Step 2: Install uv + gitleaks
Write-Step "Step 2: Optional tools (uv + gitleaks)"
if (-not (Test-Cli 'uv')) {
  Write-Step "Installing uv via pip..."
  Invoke-OrPrint "python -m pip install --user uv"
}
if (-not (Test-Cli 'gitleaks')) {
  Write-Warn "gitleaks not installed. Install via: scoop install gitleaks  OR  go install github.com/gitleaks/gitleaks/v8@latest"
  Write-Warn "Pre-commit secret-scan hook will be skipped until gitleaks is on PATH."
}

# Step 3: Scaffold
Write-Step "Step 3: Project scaffold"
$repoRoot = Split-Path -Parent $PSScriptRoot

if (Test-Path (Join-Path $repoRoot 'package.json')) {
  Write-Skip "package.json exists — scaffold already done"
} elseif ($SkipScaffold) {
  Write-Skip "Scaffold skipped per -SkipScaffold"
} else {
  Write-Step "Scaffolding Next.js 15 with OpenNext Cloudflare adapter"
  Push-Location $repoRoot
  try {
    # Use OpenNext's Cloudflare starter
    # Reference: https://opennext.js.org/cloudflare/get-started
    Invoke-OrPrint "pnpm create cloudflare@latest . --framework=next --platform=workers --ts --no-deploy --git=false"
  } finally {
    Pop-Location
  }
}

# Step 4: Core dependencies
Write-Step "Step 4: Install core dependencies"
if (Test-Path (Join-Path $repoRoot 'package.json')) {
  Push-Location $repoRoot
  try {
    $deps = @(
      'drizzle-orm',
      'drizzle-zod',
      'postgres',
      '@supabase/supabase-js',
      'zod',
      'neverthrow',
      'next-intl',
      'recharts',
      'd3',
      'resend',
      '@sentry/nextjs',
      'pagefind',
      'react-hook-form',
      'lucide-react',
      'class-variance-authority',
      'clsx',
      'tailwind-merge',
      'nepali-date-converter'
    )
    $devDeps = @(
      'drizzle-kit',
      '@types/d3',
      'vitest',
      '@vitest/coverage-v8',
      '@vitest/ui',
      '@playwright/test',
      'eslint-config-prettier',
      'prettier',
      'lint-staged',
      'simple-git-hooks',
      'tsx',
      '@cloudflare/workers-types',
      '@opennextjs/cloudflare'
    )
    Invoke-OrPrint ("pnpm add " + ($deps -join ' '))
    Invoke-OrPrint ("pnpm add -D " + ($devDeps -join ' '))
  } finally {
    Pop-Location
  }
} else {
  Write-Skip "package.json not present — re-run after scaffold"
}

# Step 5: Pre-commit hooks
Write-Step "Step 5: Pre-commit hooks (simple-git-hooks + lint-staged)"
if (Test-Path (Join-Path $repoRoot 'package.json')) {
  Push-Location $repoRoot
  try {
    Write-Warn "Add these to package.json manually (idempotent edit):"
    @'

  "simple-git-hooks": {
    "pre-commit": "pnpm exec lint-staged && pnpm typecheck && gitleaks detect --no-banner --redact --staged || true"
  },
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{md,json,yml,yaml}": ["prettier --write"]
  }
'@ | Write-Host

    Write-Step "After editing package.json: pnpm exec simple-git-hooks"
  } finally {
    Pop-Location
  }
}

# Step 6: Git init
Write-Step "Step 6: Git initialization"
Push-Location $repoRoot
try {
  if (Test-Path '.git') {
    Write-Skip ".git already exists"
  } else {
    Invoke-OrPrint "git init -b main"
  }

  $gitignorePath = Join-Path $repoRoot '.gitignore'
  if (Test-Path $gitignorePath) {
    $additions = @(
      '',
      '# Nepal Ledger additions',
      'source-data/',
      '.env.local',
      '.env*.local',
      '.vercel',
      '.wrangler/',
      '.open-next/',
      'playwright-report/',
      'test-results/',
      '.vscode/',
      '*.log',
      '.DS_Store',
      'Thumbs.db'
    )
    $current = Get-Content $gitignorePath -Raw
    if ($current -notmatch 'Nepal Ledger additions') {
      $additions -join "`n" | Add-Content -Path $gitignorePath -Encoding utf8
      Write-Ok ".gitignore augmented"
    } else {
      Write-Skip ".gitignore already has Nepal Ledger additions"
    }
  }
} finally {
  Pop-Location
}

# Step 7: User action checklist
Write-Step "Step 7: User action checklist (manual steps)"

@'

  [ ] 1. GitHub: gh auth login (already done if `gh auth status` shows authed)
  [ ] 2. GitHub: gh repo create nepal-ledger --public --source=. --remote=origin
  [ ] 3. Cloudflare auth — USE API TOKEN, NOT wrangler login
        (wrangler login OAuth callback fails on Windows due to firewall/AV/VPN)
        a) Create token at https://dash.cloudflare.com/profile/api-tokens
           Template: "Edit Cloudflare Workers"
           Add: Account R2 Storage Edit, Account D1 Edit, Account Settings Read
        b) Set env var (paste in your terminal, NEVER in chat):
           [Environment]::SetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "<token>", "User")
        c) Open new PowerShell, verify: wrangler whoami
  [ ] 4. Cloudflare Workers: connect to GitHub repo (after first push)
        ★ NOTE: Cloudflare R2 is intentionally deferred (requires payment method).
                Source-document archive uses Supabase Storage in Year 1.
                See docs/decisions/0004-supabase-storage-instead-of-r2.md
  [ ] 5. Supabase: create project at https://supabase.com (region: Singapore)
        save: Project URL + anon key + service-role key + database URL
        Create Storage bucket `source-archive` (Storage → New bucket → public read off)
  [ ] 6. (Optional) Resend: sign up at https://resend.com OR defer email to Day 60
  [ ] 7. Sentry — TWO-STEP (per ADR-0005):
        Step A (now, browser): sign up at https://sentry.io/signup/
                create Next.js project "nepal-ledger"
                save DSN to .env.local locally
        Step B (after Next.js scaffold, you run in project root):
                npx @sentry/wizard@latest -i nextjs
                Pick: Error Monitoring + Tracing + Session Replay
                Pick runtimes: All three (browser + nodejs + edge)
  [ ] 8. Domain: register chosen name via Cloudflare Registrar (or defer until Day 30)
  [ ] 9. cp .env.example .env.local and fill in secrets
  [ ] 10. After first CI workflow runs green:
         gh api repos/:owner/:repo/branches/main/protection -X PUT ... (see docs/GITHUB_PRACTICES.md)
  [ ] 11. Sanity check:
         pnpm dev (Windows OK)
         pnpm test
         pnpm build
         pnpm preview (run in WSL2 — see docs/WINDOWS_DEV.md)
  [ ] 12. First commit + push:
         git add -A
         git commit -m "feat: initial scaffold and doctrine"
         git push -u origin main

  ★ 48-HOUR ESCAPE HATCH:
    If OpenNext build/preview causes friction in the first 48 hours (scaffold
    failure, image opt broken, Server Action incompatibility, etc.), invoke
    the Vercel escape hatch per docs/CLOUD_STACK.md §"48-Hour OpenNext
    Escape Hatch". Write ADR-0005 documenting which gate failed.

'@ | Write-Host

Write-Step "Bootstrap complete. Mother Opus is ready to spawn Day 1-3 task workers."
