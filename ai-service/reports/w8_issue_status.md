# W8 GitHub issue review — 2026-10-25

Repository: `Khanggolder/AI-Smart-Parking`. Read GitHub Issues #1–#6 and PRs #7/#8 live before changes. PR #7 and #8 are merged; all six task Issues remain open. No issue was closed or checkbox changed during audit.

| Issue | Owner in issue | Evidence and disposition |
|---|---|---|
| [#1](https://github.com/Khanggolder/AI-Smart-Parking/issues/1) W0 dataset | Khang | `dataset_inspection.md` has 5 image IDs/files, 37 polygons and occupied/empty counts; five overlays are tracked and licensing/attribution noted. W8 visually opened all five overlays: polygons generally align with bays, but tree occlusion makes some empty-space interpretation uncertain. Keep open for Khang/team visual sign-off and license attribution confirmation; `Refs #1` in PR. |
| [#2](https://github.com/Khanggolder/AI-Smart-Parking/issues/2) SRS | Nam | Open; outside AI ownership. |
| [#3](https://github.com/Khanggolder/AI-Smart-Parking/issues/3) workspace/wireframe | Khôi | Open; outside AI ownership. |
| [#4](https://github.com/Khanggolder/AI-Smart-Parking/issues/4) ERD/API | Nam | PR #8 merged design documents, but backend↔AI endpoint, multipart/schema and persistence still need agreement and implementation. Keep open; `Refs #4`. |
| [#5](https://github.com/Khanggolder/AI-Smart-Parking/issues/5) split/baseline | Khang | Train/val/test manifests, day split, polygon crop code, W2 checkpoint hash and W5 independent metrics/report exist. Link PR with `Closes #5` so it closes only after review/merge. |
| [#6](https://github.com/Khanggolder/AI-Smart-Parking/issues/6) editor/dashboard | Khôi | Open; outside AI ownership. |

No existing Issue #1–#6 tracked the backend client adapter and end-to-end AI integration. Created [#10 — Connect Backend to AI Inference Service](https://github.com/Khanggolder/AI-Smart-Parking/issues/10), with Nam as proposed owner and Khang as support; the issue remains unassigned pending team coordination. Its checklist covers `/v1/infer`, multipart client, polygon mapping, stable IDs/config version, complete response validation, persistence, UNKNOWN, timeout/503/422/500, real-checkpoint and snapshot→DB integration tests, release ZIP delivery and contract update. Related PR [#9](https://github.com/Khanggolder/AI-Smart-Parking/pull/9) has `Closes #5`, `Refs #1`, `Refs #4` and `Refs #10`. No issue was closed or checkbox changed in W8.
