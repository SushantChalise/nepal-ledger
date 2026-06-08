# Live OCR dashboard — opens an auto-refreshing terminal view of the overnight
# Surya OCR run (pages done/total, rate, ETA, per-tier bars, current doc,
# heartbeat health). READ-ONLY: it only tails the _ocr_output/_state files, so
# it cannot disturb the runner/supervisor. Ctrl-C to close; the OCR keeps going.
#
# Open it any time (a visible window):
#   Start-Process powershell -ArgumentList '-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-File',
#     'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers\surya_ocr\watch_dashboard.ps1'

$py = 'C:\Users\ACER\AppData\Local\Programs\Python\Python312\python.exe'
$scrapers = 'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = $scrapers
$Host.UI.RawUI.WindowTitle = 'Nepal Ledger — overnight Surya OCR'
Set-Location $scrapers
& $py -m surya_ocr.batch_ocr watch --interval 5
