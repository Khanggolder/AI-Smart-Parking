# W6 release checklist — v0.1.0-rc1

| Hạng mục | Trạng thái | Bằng chứng / việc còn lại |
|---|---|---|
| Checkpoint SHA-256 | PASS | `488ed38e...c23608dada`; hash gốc, ZIP và sau smoke trùng |
| Config khớp checkpoint/class order/threshold | PASS | W3 JSON hash khớp frozen W5; loader kiểm hash, `empty,occupied`, 0,90 |
| Dependency và source tái lập | PASS có giới hạn | ZIP chứa source snapshot, direct version pins, Python/Torch/CUDA và hướng dẫn; chưa thử cài sạch trên máy thứ hai, chưa khóa toàn bộ transitive deps |
| Source commit ghi nhận | PASS có giới hạn | `release_manifest.json` ghi commit nền `25e1eaa529f02292d31c40914624aad1fec8c9ee` và ZIP mang source chưa commit |
| Regression tests | PASS | 34 passed, Python 3.11; loader/hash/preprocess/UNKNOWN/batch/API/error/W5 artifact audit |
| API smoke từ ZIP | PASS | GPU CUDA, 37 ID đúng thứ tự, health/ready/infer, UNKNOWN, invalid polygon/image |
| Release package hoạt động | PASS trên máy demo | 20 file checksum, `verify_release.py`; chưa thử máy khác |
| Model card | PASS | `docs/MODEL_CARD.md` |
| API contract | PASS | `docs/AI_API_CONTRACT.md` |
| Backend/frontend handover | PASS | `docs/BACKEND_HANDOVER.md`, `FRONTEND_HANDOVER.md`, client mẫu |
| Demo instructions | PASS | `docs/DEMO_RUNBOOK.md`, `scripts/demo_release.py`, ROI overlay đã xem |
| Báo cáo AI | PASS | `reports/final_ai_report.md` |
| Benchmark | PASS có phạm vi | W5 50 lượt/case/device; 37 polygon thật; 100 polygon synthetic |
| Giới hạn chưa đánh giá | PASS | Model card/final report nêu FULL, camera khác, 100 spot thật, threshold chưa production |
| Không commit model/data lớn hoặc secrets | PASS ở working tree | `releases/`, `runs/`, `data/`, `*.pt`, `.env*` được Git ignore; chưa tạo commit |
| Production readiness | NOT EVALUATED | Cần tập camera đích, FULL ground truth, triển khai mạng/backend và đánh giá mới |

Không đánh dấu PASS cho bài thử cài máy thứ hai, tích hợp backend Nam, frontend Khôi hay production.
