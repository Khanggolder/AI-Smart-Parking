# AI Smart Parking — AI service

Service nhận một ảnh JPEG/PNG của camera cố định cùng danh sách polygon ô đỗ đã cấu hình, trả `empty`, `occupied` hoặc `unknown` cho từng `spot_id`. Pipeline dùng MobileNetV3-Small pretrained checkpoint W2 (epoch 2), batch inference và ngưỡng UNKNOWN W3 `0.90` (**candidate, chưa production validated**). Service không nhận nhãn ground truth và không quyết định trạng thái nghiệp vụ FULL/STALE.

## Bắt đầu nhanh (Windows, Python 3.11)

Từ root repository:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ai-service/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn src.service:app --app-dir ai-service --host 127.0.0.1 --port 8001
```

`requirements.txt` là danh sách trực tiếp cho phát triển (gồm pytest/httpx), không phải lock file. Chạy lại W0–W5 có thêm `huggingface_hub` và `matplotlib` từ `requirements-research.txt` (`.\.venv\Scripts\python.exe -m pip install -r ai-service/requirements-research.txt`). Máy GPU cần cặp `torch`/`torchvision` phù hợp CUDA của máy; release ZIP có hướng dẫn và dependency pins đã kiểm trên máy demo. Checkpoint `ai-service/runs/mobilenetv3_gpu/best.pt` và threshold `ai-service/runs/mobilenetv3_gpu/confidence/threshold_candidate.json` phải có sẵn; cả hai bị Git ignore. Nếu thiếu/lỗi, `/health` vẫn trả 200 còn `/ready` và `/v1/infer` trả 503.

## Kiểm tra API

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8001/ready
.\.venv\Scripts\python.exe ai-service/scripts/ai_http_client.py --image <snapshot.jpg> --spots <spots.json> --camera-id CAM01
.\.venv\Scripts\python.exe -m pytest ai-service/tests -q
```

`spots.json` là array `[{"spot_id":"P01","polygon":[[x,y],...]}]`, tọa độ chuẩn hóa `[0,1]`. Client gửi multipart tới `POST /v1/infer`; dùng ảnh và polygon từ cùng camera. Schema, mã lỗi và ví dụ đầy đủ: [AI API Contract](docs/AI_API_CONTRACT.md). Với dữ liệu validation UFPR04 đã có, chạy smoke 37 polygon bằng `scripts/smoke_inference.py` hoặc kiểm bản ZIP qua `scripts/demo_release.py --version v0.1.0-rc2`.

## Cấu trúc và cấu hình

| Đường dẫn | Mục đích |
|---|---|
| `src/service.py`, `inference.py`, `preprocessing.py`, `model_loader.py`, `model_runtime.py`, `confidence_utils.py`, `w1_crop.py` | Runtime API, model, crop và UNKNOWN |
| `src/dataset.py`, `src/baseline_utils.py` | Training/evaluation; `baseline_utils.py` giữ CLI imports cũ |
| `scripts/` | Dataset W0/W1, training W2, evaluation W3/W5, benchmark W4/W5, release W6/W7 |
| `tests/`, `configs/`, `manifests/` | Regression tests, inference config, split theo ngày |
| `docs/`, `reports/` | Contract/handover/model card, bằng chứng nghiên cứu W0–W7 |
| `runs/`, `releases/` | Artifact local bị Git ignore; không xóa khi cleanup |

Config nguồn: [inference.yaml](configs/inference.yaml). Có thể ghi đè bằng `AI_CHECKPOINT_PATH`, `AI_THRESHOLD_CONFIG`, `AI_DEVICE`, `AI_BATCH_SIZE`, `AI_MAX_SPOTS`, `AI_MAX_UPLOAD_BYTES`, `AI_MAX_IMAGE_PIXELS`, `AI_PORT`. Đường dẫn tương đối được tính từ `ai-service/`; `AI_PORT` chỉ áp dụng khi chạy `python -m src.service`, còn lệnh Uvicorn trên dùng `--port`.

## Nghiên cứu, release và bàn giao

- Data preparation: `scripts/inspect_ufpr04.py`, `prepare_dataset.py`; manifests `train.csv`, `val.csv`, `test.csv` chia theo ngày. Training: `scripts/train_baseline.py`. Đánh giá: `scripts/analyze_confidence.py`, `evaluate_independent.py`, `benchmark_e2e.py`. Xem [báo cáo AI](reports/final_ai_report.md).
- W5 official test đã khóa và chạy đúng một lượt. Không dùng test để chọn model/ngưỡng hay thay đổi các artifact tại `runs/mobilenetv3_gpu/w5_evaluation/`. Xem [evaluation](reports/w5_evaluation_report.md) và [benchmark](reports/w5_benchmark_report.md).
- Release hiện hành cho integration: `releases/ai-smart-parking-model-v0.1.0-rc2.zip` (local, Git ignore). W6 `v0.1.0-rc1` được giữ nguyên. Cách cài và verify ZIP: [Release README](docs/RELEASE_README.md); nguồn release được hash trong `release_manifest.json`/`checksums.sha256`. API `model_version` vẫn là `mobilenetv3-small-w2-488ed38efe01`.
- Tích hợp: [Backend handover](docs/BACKEND_HANDOVER.md), [Backend ↔ AI integration plan](docs/BACKEND_AI_INTEGRATION_PLAN.md), [Frontend handover](docs/FRONTEND_HANDOVER.md), [Demo runbook](docs/DEMO_RUNBOOK.md), [Model card](docs/MODEL_CARD.md). Cleanup W7: [audit](reports/w7_repository_audit.md), [verification](reports/w7_verification_report.md), [change log](reports/w7_cleanup_changelog.md).
