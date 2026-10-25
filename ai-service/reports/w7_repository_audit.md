# W7 repository audit (trước cleanup)

Ngày kiểm tra: 2026-10-25. Branch: `feature/ai-dataset-inspection`; HEAD: `25e1eaa529f02292d31c40914624aad1fec8c9ee`.

## Trạng thái và phạm vi

- `git status` có `.gitignore`, `ai-service/README.md` đã sửa; hầu hết source/config/docs/tests/manifests W1–W6 chưa được track. Đây là công việc có trước W7; W7 không reset, stash hay xóa các file đó.
- `ai-service/runs/` và `ai-service/releases/` bị ignore nhưng chứa checkpoint, W3 threshold, W5 official artifacts, W6 release và demo. Không suy ra chúng có thể xóa từ trạng thái Git.
- Repo còn `backend/`, `frontend/`, `docs/` và các thư mục gốc khác; W7 chỉ sửa `ai-service/`. Không tìm thấy `AGENTS.md` trong repo.
- Checkpoint `runs/mobilenetv3_gpu/best.pt` có SHA-256 `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`. W6 `v0.1.0-rc1` có source snapshot riêng vì source W4 chưa commit. Giữ bản release này nguyên vẹn.

## Phân loại và quyết định

| File/Directory | Vai trò | Vấn đề / dependency | Đề xuất | Rủi ro |
|---|---|---|---|---|
| `src/service.py`, `inference.py`, `preprocessing.py`, `model_loader.py`, `confidence_utils.py`, `w1_crop.py` | A. Runtime | API, batch prediction, crop W1 và UNKNOWN dùng chung; thay đổi sẽ tác động release | Keep; chỉ refactor có kiểm tra response | High |
| `src/baseline_utils.py` | A/B/C. Runtime + training/evaluation | Loader runtime import module cũng chứa metrics, split checks, plotting; trách nhiệm lẫn nhau | Tách phần model/device dùng runtime, giữ import cũ cho CLI | Medium |
| `src/dataset.py` | B. Training | Dataset chỉ dùng bởi training/evaluation; không nằm trong W6 package | Keep | Low |
| `scripts/inspect_ufpr04.py`, `prepare_dataset.py`, `sample_snapshot.py` | B. Dataset/demo | `prepare_dataset` import inspector; `sample_snapshot` dùng validation metadata làm input demo | Keep entrypoint/path | Medium |
| `scripts/train_baseline.py`, `smoke_dataloader.py`, `check_w1_splits.py` | B. Training | CLI tái lập W1/W2, một số dùng import `baseline_utils` cũ | Keep compatibility | Medium |
| `scripts/analyze_confidence.py`, `evaluate_baseline.py`, `evaluate_independent.py`, `analyze_test_errors.py`, `evaluate_hard_cases.py`, `check_w1_w4_consistency.py` | C. Evaluation | Bằng chứng W2–W5, W5 test chính thức đã khóa; không dùng test để tuning | Keep | High |
| `scripts/benchmark_inference.py`, `benchmark_e2e.py`, `smoke_inference.py` | C. Benchmark/smoke | CLI và input validation; 50/100 polygon có thể lặp trong benchmark | Keep | Medium |
| `scripts/build_release.py`, `verify_release.py`, `demo_release.py`, `ai_http_client.py` | A/C. Release/integration | Build ghi version `rc1`; verifier/client được copy vào ZIP; cần giữ rc1 | Chỉ build rc2 nếu package đổi | High |
| `tests/*.py` (8 file) | D. Tests | Bảo vệ preprocessing, API, loader, confidence và W5 gate; cần so sánh trước/sau | Keep, bổ sung regression khi refactor | Medium |
| `configs/inference.yaml`, `requirements.txt` | A. Config/dependencies | Config W5 được hash; requirements gộp runtime và dev, thiếu `huggingface_hub`/`matplotlib` cho research | Giữ config/requirements; bổ sung research extras riêng | High |
| `manifests/{train,val,test}.csv` | B/F. Dataset manifest | Hash nằm trong checkpoint và W5 frozen config | Keep byte-for-byte | High |
| `docs/*.md`, `README.md` | E. Documentation | README chưa là điểm bắt đầu đầy đủ; các handover/contract đã có | Sửa README, liên kết tài liệu nguồn | Low |
| `reports/*.md`, `dataset_split_stats.json`, ảnh overlay/preview | E/F. Research evidence | W0–W6 và số liệu nghiệm thu | Keep; không sửa metrics | High |
| `runs/mobilenetv3_gpu/`, `releases/v0.1.0-rc1/`, release ZIP | F. Generated nhưng quan trọng | Ignored, chứa model/threshold/W5/release | Keep, verify hash | High |
| `runs/w2_smoke/`, `runs/w6_demo/` | F. Smoke outputs | Có thể tạo lại nhưng hữu ích để truy vết; không có lý do xóa | REVIEW_REQUIRED, keep | Low |
| `__pycache__/`, `.pytest_cache/`, `.venv/` | F. Cache/environment | Có thể tạo lại, không ảnh hưởng source | Keep tại chỗ; đã ignored | Low |
| Legacy/duplicate/unused | G. Chưa xác nhận | Không thấy file nào đủ bằng chứng để xóa; CLI không cần được import trực tiếp | Không xóa | High |

## Phương án an toàn

1. Chạy baseline tests và lưu response API thật từ 37 polygon validation, gồm nhãn, scores, threshold, version; bỏ thời gian xử lý khi so sánh.
2. Chỉ tách hàm tạo model/chọn device khỏi module training với compatibility exports. Giữ nguyên body thuật toán, preprocessing, config, checkpoint, API contract và CLI.
3. Bổ sung kiểm thử cho compatibility và so sánh response trước/sau với tolerance số thực. Chạy lại suite và smoke GPU/HTTP.
4. Nếu runtime source/package thay đổi, giữ rc1 nguyên vẹn; tạo rc2 sau khi pass, verify ZIP và smoke trực tiếp từ ZIP. Không đụng W5 official test artifacts.

`DEFERRED_BEHAVIORAL_FIXES`: Chưa có thay đổi hành vi được chấp nhận trong W7; nếu phát hiện lỗi ảnh hưởng prediction, ghi nhận thay vì sửa âm thầm.
