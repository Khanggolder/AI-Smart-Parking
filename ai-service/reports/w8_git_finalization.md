# W8 Git finalization and post-merge verification

Date: 2026-10-25. AI source branch `feature/ai-w0-w7` was created from `feature/ai-dataset-inspection` without resetting/stashing user work. Original AI W0 commit: `25e1eaa529f02292d31c40914624aad1fec8c9ee`. Audited W1–W7 source commit: `f9bd78c` (`feat(ai): complete W0-W7 inference service and evaluation`), 67 files: `.gitignore` and `ai-service/` only. Merge commit `11908bf` imports `origin/main` at `8b307a296bcc14bd8cbad8149146676f29e58865` with no conflicts; it added Nam's three backend design documents unchanged. Documentation commit `68d2557` records verification and handover. `git diff origin/main...HEAD` contains no backend/frontend/docs changes beyond the AI branch's own files. No force push, reset, branch deletion or PR merge was performed.

## Staging and repository checks

- `git diff --cached --check` passed before AI commit. Staged inventory contained no `.pt/.pth/.onnx/.ckpt`, ZIP, `.env`, raw images/crops, `runs/`, `releases/`, backend or frontend path. Text credential scan found no secrets; only explanatory references. Manifests have relative paths and labels. Existing five W0 overlays and inspector were already in Git.
- `.gitignore` now excludes `releases/`; `runs/`, datasets, weights and virtual environments remain ignored. Ignored artifacts were neither staged nor deleted.
- Feature tree was clean after merge. Three backend design documents came from main; AI source/config/metrics were not overwritten. The main branch itself was not changed locally or remotely.

## Verification after merge

| Gate | Observed result |
|---|---|
| `python -m pytest ai-service/tests -q` | 34 passed in 13.23s |
| `scripts/w7_regression.py --compare runs/w7/after.json` | MATCH: full business response excluding timing, 37 spots, CUDA, model version; float tolerance `1e-6` |
| `scripts/demo_release.py --version v0.1.0-rc2` | Extracted ZIP, 21 checksummed files; `/health` alive, `/ready` ready, 37 predictions and preserved spot IDs/order, UNKNOWN development crop, 422 invalid polygon/image |
| `verify_release.py` | rc1 verified 20 files; rc2 verified 21 files |
| ZIP and checkpoint SHA-256 | rc2 ZIP `6073421790203b850f71e6b013ad49a2ae3b42417ec00ec08236483a1603b27a`; checkpoint `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada` |
| Release source content | Eight packaged `src/*.py` files byte-equal to local files and AI commit `f9bd78c` Git blobs. Class order `empty`, `occupied`; threshold `0.90`; model version `mobilenetv3-small-w2-488ed38efe01`. |
| `git diff --check origin/main...HEAD` | PASS |

The rc2 `release_manifest.json` **still records `source_commit=25e1eaa`**, the W0 base at package build time. Its `source_snapshot` explicitly says W7 uncommitted source; the ZIP was built before commit `f9bd78c`, even though the eight packaged source files are byte-identical to that later commit. This distinction is preserved; no historical manifest was edited and no rc3 was built because code/weights/config are unchanged. The ZIP is distributed separately from Git. W5 official test was not rerun or used for tuning.

## GitHub review state

Branch was pushed to `origin/feature/ai-w0-w7`. [PR #9 — feat(ai): Complete W0–W7 AI Inference Service](https://github.com/Khanggolder/AI-Smart-Parking/pull/9) targets `main`, remains open and unmerged. Review requests were sent to Nam (`hoainam190205`) and Khôi (`mkay263`). PR links `Closes #5` and references #1, #4 and [integration Issue #10](https://github.com/Khanggolder/AI-Smart-Parking/issues/10). No issue was closed in W8. GitHub's mergeability field was still calculating (`unknown`) when first fetched; review/merge must wait for GitHub's final check and team approval.

## Integration and remaining gates

The backend contract in merged PR #8 uses `/predict`, one metadata JSON field, polygon objects and `inference_ms`; AI runtime uses `/v1/infer`, separate multipart fields, coordinate pairs and `processing_time_ms`. `ai-service/docs/BACKEND_AI_INTEGRATION_PLAN.md` gives mapping, timeout/error handling and tests. Nam must agree on the adapter and update his contract/implementation. Release ZIP delivery channel and target-machine install remain to be arranged; cloning GitHub does not supply weights. W0 Issue #1 awaits human sign-off on tree-obscured overlays and attribution. W1 AI Issue #5 is eligible for PR-linked closure after review/merge. No end-to-end backend/DB/frontend integration or production validation is claimed.
