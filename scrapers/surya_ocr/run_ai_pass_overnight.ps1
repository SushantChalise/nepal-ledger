# Overnight AI-pass supervisor — walk the Master Recovery Ledger in value order,
# recover each pending table via the ocr-table-recovery Workflow (driven by a
# headless `claude` Mother session per batch), update the ledger, and write the
# morning report. RECOVER + STAGE ONLY — never promotes, never writes the DB.
#
# Mirrors run_overnight.ps1 (the Surya OCR supervisor): bounded, checkpointed,
# resumable, crash-restartable. The ledger IS the checkpoint — a relaunch skips
# already-done tables (ledger_driver `next` only emits status==pending).
#
# SAFE BY DEFAULT: without -Execute it DRY-RUNS (prints the batch it would
# recover) so you can eyeball value-order + dispatch args before spending tokens.
#
#   # dry run (no tokens spent) — see what it would do:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scrapers\surya_ocr\run_ai_pass_overnight.ps1
#   # real run (spends tokens; launches headless claude per batch):
#   ... run_ai_pass_overnight.ps1 -Execute -MaxIterations 80 -BatchSize 1
#
# Telemetry under _ai_pass/REPORTS/: ai_pass_supervisor.log + the dated report.

param(
  [int]$MaxIterations = 200,   # hard cap on batches (runaway backstop)
  [int]$BatchSize = 1,         # tables per headless claude session
  [int]$MaxPages = 8,          # skip tables larger than this (run big ones deliberately)
  [string]$Tier = '',          # optional: restrict to one tier e.g. P0
  [switch]$SingleOnly,         # only single-page tables (existing engine path)
  [switch]$Execute             # actually launch claude; omit for a dry run
)

$ErrorActionPreference = 'Continue'
$py = 'C:\Users\ACER\AppData\Local\Programs\Python\Python312\python.exe'
$root = 'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4'
$driver = Join-Path $root 'scrapers\surya_ocr\_ai_pass\ledger_driver.py'
$reports = Join-Path $root 'scrapers\surya_ocr\_ai_pass\REPORTS'
$wfSingle = Join-Path $root 'scrapers\surya_ocr\workflows\ocr_table_recovery.js'
$wfMulti = Join-Path $root 'scrapers\surya_ocr\workflows\ocr_table_recovery_multipage.js'
$env:PYTHONUTF8 = '1'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$log = Join-Path $reports 'ai_pass_supervisor.log'
function Log($m) { ((Get-Date -Format o) + ' ' + $m) | Tee-Object -Append -FilePath $log }

Set-Location $root
Log ("supervisor START pid=$PID execute=$($Execute.IsPresent) batch=$BatchSize maxIter=$MaxIterations")

for ($i = 0; $i -lt $MaxIterations; $i++) {
  # 1) next batch of pending tables (value order) from the ledger
  $nextArgs = @($driver, 'next', '--n', $BatchSize, '--max-pages', $MaxPages)
  if ($Tier) { $nextArgs += @('--tier', $Tier) }
  if ($SingleOnly) { $nextArgs += '--single-only' }
  $batchJson = & $py @nextArgs
  $batch = $batchJson | ConvertFrom-Json
  if (-not $batch -or $batch.Count -eq 0) {
    Log 'ledger drained (no pending tables match the filter) — DONE'
    break
  }

  foreach ($t in $batch) {
    $wf = if ($t.multipage) { $wfMulti } else { $wfSingle }
    $argsJson = ($t.args | ConvertTo-Json -Compress -Depth 8)
    Log ("iter=$i table=$($t.id) tier=$($t.tier) pages=$($t.n_pages) multipage=$($t.multipage) wf=$([System.IO.Path]::GetFileName($wf))")

    if (-not $Execute) {
      Log ("  DRY: would recover $($t.id) - hint: $($t.table_hint)")
      continue
    }

    # 2) one headless Mother session recovers this table + updates the ledger.
    #    It must: run the Workflow {scriptPath=$wf, args=$t.args}; read the gate;
    #    then `ledger_driver.py update`. RECOVER+STAGE ONLY — no DB writes.
    $prompt = @"
You are Mother on Nepal Ledger, recovering ONE OCR table NON-INTERACTIVELY.
Run the Workflow tool with scriptPath="$wf" and args=$argsJson (pass args as a JSON object).
Wait for it to finish. Then map the gate result to a ledger status:
 - reconciled (matrix_reconciles / grand_total_reconciles true)  -> recovered
 - structural_decision_needed non-empty                          -> needs-decision
 - otherwise                                                     -> quarantined
Then run exactly:
  $py "$driver" update --id $($t.id) --status <status> --residual <worst_residual> --artifact "$($t.args.out_dir)" --note "<one line>"
RECOVER + STAGE ONLY. Do NOT write to any database or schema. Do NOT promote. Then stop.
"@
    # --print = headless; allow the tools the workflow needs. Tune to your CLI.
    & claude --print --permission-mode acceptEdits $prompt 2>&1 | Out-File -Append -Encoding utf8 $log
    Log ("  claude exit=$LASTEXITCODE for $($t.id)")
  }

  # 3) refresh the morning report after each batch (checkpoint the human view)
  & $py $driver report | Out-Null
}

& $py $driver report
Log ("supervisor STOP pid=$PID")
