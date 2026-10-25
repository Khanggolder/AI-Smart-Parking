# W8 Git audit — 2026-10-25

## Snapshot before W8 commit

- Branch: `feature/ai-dataset-inspection`; HEAD `25e1eaa529f02292d31c40914624aad1fec8c9ee`; remote same. `origin/main` fetched at `8b307a296bcc14bd8cbad8149146676f29e58865` (PR #8 merge). Divergence: AI branch 1 commit ahead, 4 commits behind main. `feature/ai-w0-w7` did not exist locally or on GitHub at audit time.
- Working tree contains pre-existing modifications to `.gitignore` (ignore `releases/`) and `ai-service/README.md`, plus 62 untracked AI files. No staged changes. W1–W7 runtime, training, evaluation, configs, manifests, tests and reports were absent from Git. W0 inspector/report and five sample overlays were already tracked in the AI branch.
- `origin/main` adds Nam's W1 backend design documents under `docs/`; no backend/frontend working-tree modifications are present. `CONTRIBUTING.md` requires feature branch, review PR, tests, and no large data/model/secrets. No repository `AGENTS.md` was found.
- Ignored: `ai-service/runs/` (checkpoint, threshold, W5 evidence and smoke output), `ai-service/releases/` (rc1/rc2 packages), Python caches and `.venv`. These are preserved locally and excluded from the proposed commit. `.gitignore` also protects `data/`, `datasets/`, weights extensions and `.env*`.

## File audit and risks

| Group | Decision | Evidence / risk |
|---|---|---|
| `src/`, `scripts/`, `tests/`, `configs/`, `requirements*.txt` | Commit AI source, tests, safe config and dependencies | Needed for W0–W7 reproducibility; no runtime/threshold edits in W8. |
| `manifests/{train,val,test}.csv` | Commit | Relative paths, annotations and labels only; no image bytes or local absolute paths. Hashes are frozen by W5. |
| `docs/`, `reports/*.md`, split statistics, `crops_preview.jpg` | Commit | Technical evidence and a small preview. W0's five sample overlays were already tracked. |
| `runs/`, `releases/`, caches, virtual env | Exclude | Weights, official W5 outputs, ZIP and generated artifacts; keep locally. |
| Backend/frontend source and contracts | Preserve | Nam/Khôi own them. Only read/compare; integration mismatch documented separately. |

Text scan of candidate AI files found no credential value, private key, GitHub/Hugging Face token or absolute `C:\Users` path. Matches for “secret/password/token” were explanatory text only. The preview image is 165 KB; no dataset image or bulk crop is in the untracked set. Model checkpoint SHA-256 is `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`; W3 threshold file SHA-256 is `cb4270f8adae58ec4dede8e2b9267896523f120b74da614f1328f9a68d84784a`.

## Gate before push

Create `feature/ai-w0-w7` without discarding working-tree changes; stage only `.gitignore` and `ai-service/` candidate files; inspect `git diff --cached --name-only`, `--stat`, `--check`, and staged content/security scan. Commit, merge fetched `origin/main`, run regression and rc2 smoke, compare release source and checkpoint, then push/open PR only if all gates pass. Never force push, reset, or choose merge sides wholesale.
