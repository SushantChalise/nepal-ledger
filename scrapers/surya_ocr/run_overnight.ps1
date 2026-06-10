# Overnight Surya OCR supervisor — auto-restart the bulk runner until the
# prioritized queue is drained. Surya is delicate: a CUDA fault / OOM can kill
# the Python process. This loop restarts it; the runner resumes from its
# per-page checkpoints (skip-if-exists), so no work is lost or repeated.
#
# Launch DETACHED so it survives the controlling session (NO -WindowStyle so
# startup errors are catchable via -RedirectStandardError):
#   Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',
#     'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers\surya_ocr\run_overnight.ps1'
#
# Telemetry the Mother monitor reads (under _ocr_output/_state/):
#   supervisor.log   lifecycle + per-restart progress
#   progress.log     per-page OK/ERROR (+ FATAL traceback) from the runner
#   heartbeat.json   {ts, pid, last_path, done_this_run, ...}
#   DONE             written when the queue is fully drained

$ErrorActionPreference = 'Continue'
$py = 'C:\Users\ACER\AppData\Local\Programs\Python\Python312\python.exe'
$scrapers = 'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers'

$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = $scrapers
$env:TQDM_DISABLE = '1'

$state = Join-Path $scrapers 'surya_ocr\_ocr_output\_state'
New-Item -ItemType Directory -Force -Path $state | Out-Null
$log = Join-Path $state 'supervisor.log'
$donefile = Join-Path $state 'DONE'

function Log($m) { ((Get-Date -Format o) + ' ' + $m) | Out-File -Append -Encoding utf8 $log }

Set-Location $scrapers
Log ('supervisor START pid=' + $PID)
Remove-Item -Force $donefile -ErrorAction SilentlyContinue

for ($i = 0; $i -lt 500; $i++) {
    Log ('launch runner attempt=' + $i)
    & $py -m surya_ocr.batch_ocr run 2>$null | Out-Null
    Log ('runner exited code=' + $LASTEXITCODE)

    $st = $null
    try { $st = (& $py -m surya_ocr.batch_ocr status 2>$null | ConvertFrom-Json) } catch { }
    if ($null -ne $st) {
        Log ('progress done=' + $st.pages_done + '/' + $st.pages_total + ' err=' + $st.pages_error + ' pct=' + $st.pct + ' docs=' + $st.docs_complete + '/' + $st.docs_total)
        if ($st.resolved_ge_total) {
            Log 'DONE queue drained'
            ('done ' + (Get-Date -Format o) + ' done=' + $st.pages_done + ' err=' + $st.pages_error) | Out-File -Encoding utf8 $donefile
            break
        }
    } else {
        Log 'status unavailable'
    }
    Start-Sleep -Seconds 15
}
Log ('supervisor STOP pid=' + $PID)
