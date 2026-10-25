# W8 GitHub issue review — 2026-10-25

Repository: `Khanggolder/AI-Smart-Parking`. Read GitHub Issues #1–#6 and PRs #7/#8 live before changes. PR #7 and #8 are merged; all six task Issues remain open. No issue was closed or checkbox changed during audit.

| Issue | Owner in issue | Evidence and disposition |
|---|---|---|
| [#1](https://github.com/Khanggolder/AI-Smart-Parking/issues/1) W0 dataset | Khang | `dataset_inspection.md` has 5 image IDs/files, 37 polygons and occupied/empty counts; five overlays are tracked and licensing/attribution noted. Report explicitly says manual visual inspection remains required. Keep open; `Refs #1` in PR until visual sign-off. |
| [#2](https://github.com/Khanggolder/AI-Smart-Parking/issues/2) SRS | Nam | Open; outside AI ownership. |
| [#3](https://github.com/Khanggolder/AI-Smart-Parking/issues/3) workspace/wireframe | Khôi | Open; outside AI ownership. |
| [#4](https://github.com/Khanggolder/AI-Smart-Parking/issues/4) ERD/API | Nam | PR #8 merged design documents, but backend↔AI endpoint, multipart/schema and persistence still need agreement and implementation. Keep open; `Refs #4`. |
| [#5](https://github.com/Khanggolder/AI-Smart-Parking/issues/5) split/baseline | Khang | Train/val/test manifests, day split, polygon crop code, W2 checkpoint hash and W5 independent metrics/report exist. Link PR with `Closes #5` so it closes only after review/merge. |
| [#6](https://github.com/Khanggolder/AI-Smart-Parking/issues/6) editor/dashboard | Khôi | Open; outside AI ownership. |

No existing Issue #1–#6 specifically tracks the backend client adapter and end-to-end AI integration. Search the complete current Issue list before creating a new one. Draft: **`[Integration][BE↔AI] Connect Backend to AI Inference Service`**. Owner Nam; support Khang; related #4 and AI PR. Checklist: agree `/v1/infer`; implement multipart client; convert `{x,y}` to `[x,y]`; preserve ordered stable spot UUIDs and camera/polygon version; verify complete response; store label/raw label/confidence/scores/model version/threshold/capture time; preserve UNKNOWN; handle timeout/503/422/500 without fake or partial predictions; test real checkpoint and snapshot→backend→AI→DB; update contract together; confirm with Nam before closure. Do not assign a GitHub username without verification.
