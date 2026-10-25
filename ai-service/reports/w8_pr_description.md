# PR draft — feat(ai): Complete W0–W7 AI Inference Service

## Summary

Add the AI work from W0–W7 on `feature/ai-w0-w7`: MetaPKLot UFPR04 inspection, day-separated train/val/test manifests and polygon crop preparation, MobileNetV3-Small W2 training, W3 UNKNOWN threshold analysis, FastAPI inference, frozen W5 independent evaluation/benchmarks, rc1/rc2 release tooling and W7 safe runtime refactor. Merge current `main` backend design documents without changing them.

## Evidence

- W5 independent test: 740 crops, raw accuracy **97.973%**, occupied F1 **97.288%**. With frozen `0.90` threshold: 28 UNKNOWN, 712 accepted, 2 accepted false empty. Full-lot false-alarm rate was not evaluated.
- Checkpoint SHA-256: `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`; model version `mobilenetv3-small-w2-488ed38efe01`, class order `empty, occupied`.
- Post-merge: 34 tests passed; W7 full-response regression MATCH; rc2 extracted ZIP smoke passed `/health`, `/ready`, 37 distinct spot IDs/order, UNKNOWN and 422 cases. rc1/rc2 verifiers passed. rc2 ZIP SHA-256 `6073421790203b850f71e6b013ad49a2ae3b42417ec00ec08236483a1603b27a`.
- rc2 ZIP is ignored by Git and must be delivered internally. Its manifest names old W0 base commit because it was built before W7 source was committed; eight packaged source files are byte-identical to new AI commit `f9bd78c`. Historical manifest left intact.

## Integration and limits

AI endpoint is `POST /v1/infer` with multipart `image`, `camera_id`, `spots_json` and normalized `[x,y]` vertices. Current backend design says `/predict` with metadata JSON and `{x,y}` vertices. [Adapter plan](https://github.com/Khanggolder/AI-Smart-Parking/blob/feature/ai-w0-w7/ai-service/docs/BACKEND_AI_INTEGRATION_PLAN.md) documents request/response mapping, errors, retries and tests for Nam; the two contracts were not silently changed. Backend owns snapshot jobs, stable spot/camera/polygon version, persistence, FULL and STALE. UNKNOWN stays distinct. Dashboard uses final label: green empty, red occupied, gray unknown. Service has no authentication; deploy on private network. Threshold and UFPR04 metrics are not production validation or cross-camera guarantees.

## Review

Please review AI source/evidence and integration plan. Nam should review the contract mapping; Khôi should review dashboard handover. No backend/frontend code changed. Release package transfer and a real end-to-end integration test remain for follow-up.

Closes #5
Refs #1
Refs #4
Refs #10
