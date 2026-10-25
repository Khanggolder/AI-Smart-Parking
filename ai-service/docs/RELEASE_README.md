# AI Smart Parking v0.1.0-rc2 — release candidate

Gói này tự chứa checkpoint đã xác minh, source **inference** sau cleanup W7, cấu hình và tài liệu. Không có tập ảnh/dữ liệu gốc. `release_manifest.json` ghi commit nền và `checksums.sha256` ghi hash từng file vì source W1–W7 chưa commit trong commit nền. `model_version` API là `mobilenetv3-small-w2-488ed38efe01`; release version là `v0.1.0-rc2`. W6 `v0.1.0-rc1` được giữ nguyên làm bản tham chiếu. W7 chỉ tách model/device helpers, không thay đổi weights, preprocessing hay API.

## Khôi phục trên Windows / Python 3.11

Giải nén ZIP, vào thư mục `v0.1.0-rc2` bằng PowerShell. Với GPU CUDA 12.8 tương thích, cài đúng cặp wheel đã kiểm trên máy demo:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0+cu128 torchvision==0.26.0+cu128 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
```

Nếu dùng CPU, cài cặp `torch==2.11.0+cpu`/`torchvision==0.26.0+cpu` từ index CPU tương ứng, đặt `$env:AI_DEVICE='cpu'`. Các phiên bản này cần được kiểm tra sẵn có và thử trên máy đích. `requirements-demo.txt` pin dependency trực tiếp; pip giải quyết transitive dependencies, nên đây chưa phải wheelhouse/lock toàn bộ nền tảng. Cần Internet hoặc wheel cache tương ứng để cài.

Kiểm hash trước khi chạy:

```powershell
.\.venv\Scripts\python.exe verify_release.py
```

Chạy local:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.service:app --app-dir . --host 127.0.0.1 --port 8001
```

`GET http://127.0.0.1:8001/health` báo process sống; `/ready` phải có `status=ready`, đúng `model_version`, threshold `0.9`. Khi cấu hình/checkpoint lỗi, `/health` có thể vẫn 200 nhưng `/ready` và inference trả 503. Để bind trong Docker, chỉ mở tới backend qua mạng nội bộ; endpoint hiện chưa xác thực.

Biến môi trường `AI_CHECKPOINT_PATH`, `AI_THRESHOLD_CONFIG`, `AI_DEVICE`, `AI_BATCH_SIZE`, `AI_MAX_SPOTS`, `AI_MAX_UPLOAD_BYTES`, `AI_MAX_IMAGE_PIXELS` ghi đè cấu hình. Đường dẫn tương đối được giải từ thư mục release. `AI_PORT` chỉ dùng khi chạy `python -m src.service`; với Uvicorn CLI dùng `--port`.

Smoke: dùng `client_example.py --image <snapshot.jpg> --spots <spots.json> --camera-id CAM01` với polygon đã cấu hình cho đúng ảnh. File JSON là array `[{"spot_id":"P01","polygon":[[x,y],...]}]`; client không gửi nhãn ground truth. Xem `AI_API_CONTRACT.md` cho schema, mã lỗi và giới hạn. Với repo nguồn và dữ liệu validation có sẵn, `scripts/demo_release.py --version v0.1.0-rc2` kiểm ảnh UFPR04 37 polygon thực qua HTTP trên máy demo.

Tương thích đã xác nhận: Windows 64-bit, Python 3.11.0, PyTorch 2.11.0+cu128, torchvision 0.26.0+cu128, RTX 3050 Laptop GPU và CPU của máy demo. Máy khác, driver khác, Linux/Docker và cài mới từ Internet chưa được kiểm chứng. Đây không phải bản production.
