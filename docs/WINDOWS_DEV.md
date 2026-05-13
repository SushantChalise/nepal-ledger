# Windows Development Doctrine

The user environment is Windows 11 with PowerShell. The deployment target is Cloudflare Workers via the OpenNext adapter. OpenNext's own documentation flags Windows-only development as not fully supported; production-like preview should run in WSL2 or Linux CI. This document codifies how to split work safely.

---

## TL;DR

| Activity | Where |
|----------|-------|
| Day-to-day editing, commits, doc work | **Windows PowerShell** (native) |
| `pnpm dev` (Next.js local dev server) | **Windows PowerShell** (works fine) |
| Drizzle migrations, schema work | **Windows PowerShell** |
| `pnpm test` (Vitest) | **Windows PowerShell** |
| `pnpm build` for production check | **WSL2 Ubuntu** |
| `pnpm preview` via OpenNext (Cloudflare Workers local) | **WSL2 Ubuntu** |
| `wrangler deploy` to production | **WSL2 Ubuntu** OR **GitHub Actions** (preferred) |
| Python scrapers (`pdfplumber`, `httpx`) | **Either** — Python multiplatform |
| Playwright E2E | **Either** — but install browsers in both environments separately |

**Rule of thumb:** if the bug only reproduces on Windows local dev, do not assume it's real. Reproduce in WSL2 OR GitHub Actions CI first.

---

## Why This Split

Cloudflare Workers + OpenNext uses `workerd` and depends on Unix-like build tooling (esbuild, wasm builds, certain native modules). The OpenNext team explicitly notes Windows is not guaranteed for the build/preview flow. Things that have historically broken on Windows:

- `next build` on certain Node versions with specific image-optimization paths
- `wrangler dev` with route patterns that resolve case-insensitively
- File-watching with very deep `node_modules` trees on NTFS
- Line-ending differences (CRLF vs LF) in source maps and lockfiles

These are not theoretical — they cost hours of "is this a real bug or a Windows artifact" investigation. We sidestep entirely by doing production-like build + preview in WSL2.

---

## WSL2 Setup (one-time)

Already installed? Skip. To check: in PowerShell run `wsl --status`. If you see a default distro, you have it.

If not:

```powershell
# Install WSL2 (requires admin)
wsl --install -d Ubuntu

# After reboot, set up Ubuntu user, then:
wsl
```

Inside WSL2 Ubuntu:

```bash
# Install Node via nvm (matches the .nvmrc in our repo)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
exec bash
nvm install --lts
npm install -g pnpm

# Install gh, git (often present)
sudo apt update && sudo apt install -y gh git build-essential

# Authenticate the same way as Windows
gh auth login

# Access the repo
cd /mnt/c/Users/ACER/Projects/Economy

# OR clone fresh into the Linux filesystem (faster I/O)
mkdir -p ~/work && cd ~/work
git clone <repo-url>
cd <repo-name>
pnpm install
```

**File-system tip:** running `pnpm install` and `next build` against `/mnt/c/...` is much slower than running against the Linux home dir. For active OpenNext build/preview work, clone the repo into `~/work/` and push changes from there. For routine editing, stay on the Windows-mounted path (file watchers across the WSL boundary still work via VS Code Remote-WSL).

---

## VS Code + WSL2 Workflow

The smoothest pattern:

1. Open the repo in VS Code on Windows. Make edits, commit, push.
2. For OpenNext build/preview, open the WSL2 terminal pane (VS Code's integrated terminal supports WSL).
3. Run `pnpm preview` from inside WSL2.
4. The Cloudflare Workers local preview URL is accessible from Windows browsers normally.

This avoids the cognitive overhead of two separate editor sessions.

---

## What NEVER Runs On Windows

- `wrangler deploy --env production` (use GitHub Actions; manual deploys only as last resort, from WSL2)
- Any "fix it because it's broken on prod" investigation that starts from a Windows-only repro (always confirm the bug in WSL2 or CI first)
- The first time you run a new OpenNext upgrade (run in WSL2, then GHCI, then trust Windows)

---

## What ALWAYS Works On Windows

- Reading/editing source
- Git operations (`git`, `gh`)
- `pnpm install`, `pnpm dev` (Next.js without OpenNext)
- `pnpm test` (Vitest)
- `pnpm lint`, `pnpm typecheck`
- Drizzle Kit operations (`pnpm drizzle-kit generate`, `migrate`)
- Python scrapers (`uv pip install`, parser runs)
- All the doctrine doc work
- GitHub PR creation
- Reading logs from Cloudflare dashboard

---

## CI as the Final Arbiter

GitHub Actions (Ubuntu runners) is the **authoritative build environment**. If CI is green, the change is shippable, regardless of what local dev showed. This is why we want full CI parity (typecheck, lint, test, build, OpenNext build, gitleaks) running on every PR — see [GITHUB_PRACTICES.md](GITHUB_PRACTICES.md) §"CI Job".

When a worker (Sonnet) reports "build passes locally," Mother still waits for CI to pass before integrating. The cost of waiting 2 minutes for CI is much less than the cost of a CRLF or Windows-path bug landing on main.

---

## Cross-Reference

- Deployment doctrine: [CLOUD_STACK.md](CLOUD_STACK.md) §"Cloudflare Workers + OpenNext"
- CI workflow: `.github/workflows/ci.yml`
- Bootstrap script (PowerShell): `scripts/bootstrap.ps1` — Windows-native; sets up everything except OpenNext preview
- OpenNext upstream docs: https://opennext.js.org/cloudflare
- Cloudflare Workers Next.js guide: https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/
