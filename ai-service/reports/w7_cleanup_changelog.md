# W7 cleanup change log

## Phạm vi thay đổi W7

| File | Thay đổi | Lý do |
|---|---|---|
| `src/model_runtime.py` (mới) | Chuyển nguyên logic tạo MobileNetV3-Small, class order và chọn device từ `baseline_utils.py` | Runtime loader không phải import metrics, split checks, plotting của training/evaluation |
| `src/model_loader.py` | Import ba helper từ `model_runtime.py` | Dependency runtime rõ ràng hơn; không đổi logic load/check hash/predict |
| `src/baseline_utils.py` | Re-export ba helper theo cả import package và legacy top-level | Giữ CLI W1–W3 và evaluation scripts hiện có; metrics/plotting không đổi |
| `scripts/w7_regression.py` (mới) | Capture và so sánh HTTP response từ validation, gồm 37 polygon, UNKNOWN và lỗi | Regression gate trước/sau, không dùng nhãn test |
| `scripts/build_release.py` | Chuyển target sang `v0.1.0-rc2`, đóng gói `model_runtime.py` | Runtime source trong ZIP phải khớp source W7; không ghi đè rc1 |
| `scripts/demo_release.py` | Chọn `--version`, ghi smoke W7 vào `runs/w7_demo/` | Smoke rc2 từ ZIP, giữ W6 output và rc1 nguyên vẹn |
| `requirements-research.txt` (mới) | Thêm `huggingface_hub` và `matplotlib` phiên bản hiện cài | Đủ dependency trực tiếp cho dataset inspection và research plots, không đổi đường cài runtime W6 |
| `README.md` | Viết lại hướng dẫn cài/chạy/test, cấu trúc, nguồn config và tài liệu | Một điểm bắt đầu cho người mới |
| `docs/RELEASE_README.md`, `MODEL_CARD.md`, `BACKEND_HANDOVER.md`, `DEMO_RUNBOOK.md` | Đánh dấu release hiện hành rc2 và giới hạn kế thừa W5 | Tránh hướng dẫn dùng nhầm rc1 |
| `reports/w7_repository_audit.md`, `w7_cleanup_changelog.md`, `w7_verification_report.md`, `w7_integration_readiness.md` (mới) | Audit, thay đổi, bằng chứng và bàn giao | Review được theo từng bước |

Không di chuyển, hợp nhất hoặc xóa file nào. `.gitignore`, `configs/inference.yaml`, manifests, checkpoint, W3 threshold, W5 official artifacts, W6 rc1 và phần backend/frontend giữ nguyên so với đầu W7. Các thay đổi `.gitignore` cùng phần lớn source W1–W6 đã có trước W7 và vẫn chưa commit. Artifact W7 thêm trong `runs/w7/`, `runs/w7_demo/` và `releases/v0.1.0-rc2/`/ZIP; tất cả Git ignored.

## Giữ nguyên và hoãn

- Giữ `w1_crop.py`, preprocessing, confidence decision và API schema nguyên vẹn vì dữ liệu W5 gắn với đúng pipeline này.
- Giữ mọi CLI/research report W0–W6 và W5 official artifacts để tái lập và audit. `baseline_utils.py` vẫn được copy vào rc2 cho compatibility, dù runtime không import nó; loại khỏi package sẽ cần một release candidate tiếp theo.
- Giữ `runs/w2_smoke/` và `runs/w6_demo/` (`REVIEW_REQUIRED`), không tự xóa artifact ngoài cache.
- `DEFERRED_BEHAVIORAL_FIXES`: không phát hiện/sửa hành vi dự đoán trong W7. Các giới hạn sản phẩm (false empty được chấp nhận, camera khác, FULL/STALE) cần đánh giá/tích hợp riêng, không đổi âm thầm rồi dùng lại metrics W5.

## Đề xuất review Git

Commit message đề xuất: `refactor(ai): isolate runtime model helpers and verify W7 release`

Pull Request description đề xuất:

> Tổ chức lại AI service sau W0–W6: tách model/device helpers khỏi training utilities, giữ legacy CLI imports, bổ sung regression capture/compare cho 37 polygon validation và tài liệu bắt đầu/bàn giao. Tạo release candidate local `v0.1.0-rc2`; giữ `rc1` nguyên hash. Trước/sau: 34 tests PASS, response inference/UNKNOWN/error khớp, checkpoint SHA không đổi; rc2 ZIP verify 21 files và HTTP smoke CUDA PASS. Không chạy lại W5 official test hay huấn luyện. Source W1–W6 hiện chưa commit và cần được review cùng W7; ZIP/checkpoint Git ignored nên cần kênh phân phối artifact riêng.
