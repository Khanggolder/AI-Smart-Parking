# Hợp đồng API inference W4

Dịch vụ AI xử lý **một snapshot** từ camera cố định, không lưu dữ liệu. [Hợp đồng backend](../../docs/api/backend-api-contract-v1.md) hiện mô tả `/predict` và metadata khác với API `/v1/infer` này; [kế hoạch tích hợp](BACKEND_AI_INTEGRATION_PLAN.md) nêu mapping để Nam review trước khi có adapter.

## Endpoint

| Method | Path | Ý nghĩa |
|---|---|---|
| GET | `/health` | Tiến trình còn sống; `200 {"status":"alive"}` kể cả khi model chưa sẵn sàng. |
| GET | `/ready` | `200` khi checkpoint đã load, trả `status`, `device`, `model_version`, `threshold`; nếu không, `503 MODEL_UNAVAILABLE`. |
| POST | `/v1/infer` | Một ảnh và 1–100 ô; trả kết quả theo đúng thứ tự danh sách đầu vào. |

`POST /v1/infer` dùng `multipart/form-data` với ba trường bắt buộc:

- `image`: file JPEG hoặc PNG, mặc định tối đa 10 MiB và 20 triệu pixel. MIME và nội dung ảnh đều được kiểm tra.
- `camera_id`: chuỗi 1–128 ký tự, không toàn khoảng trắng; service chỉ echo ID này.
- `spots_json`: chuỗi JSON array. Mỗi phần tử có `spot_id` chuỗi duy nhất 1–128 ký tự và `polygon` gồm 3–50 cặp số `[x,y]` trong `[0,1]`. Tối đa 100 ô; polygon không được suy biến, trùng đỉnh hoặc tự giao.
  Toàn bộ chuỗi `spots_json` tối đa 256 KiB.

Ví dụ `spots_json`:

```json
[{"spot_id":"P01","polygon":[[0.12,0.30],[0.20,0.30],[0.21,0.45],[0.11,0.45]]}]
```

Tọa độ normalized được nhân với `width - 1`, `height - 1` rồi làm tròn đến pixel gần nhất. `0` là pixel đầu, `1` là pixel cuối. Ảnh phải cùng góc camera đã dùng khi tạo polygon; service không thể xác thực việc camera bị dịch chuyển. `spot_id` do backend gửi, không lấy từ annotation.

Phản hồi `200`:

```json
{
  "camera_id": "CAM01",
  "model_version": "mobilenetv3-small-w2-488ed38efe01",
  "threshold": 0.9,
  "predictions": [{"spot_id": "P01", "raw_label": "occupied", "label": "occupied", "confidence": 0.97,
                   "scores": {"empty": 0.03, "occupied": 0.97}}],
  "processing_time_ms": 120.0
}
```

Số trong ví dụ chỉ minh họa. `model_version` lấy từ tên model và 12 ký tự đầu SHA-256 checkpoint. Class order là `empty = 0`, `occupied = 1`. `scores` là softmax hai lớp, có tổng xấp xỉ 1. `confidence` là điểm softmax lớn nhất, **không phải xác suất đúng đã hiệu chuẩn**. `raw_label` là lớp có score lớn nhất; `label` bằng `unknown` khi `confidence < threshold`, còn tại ngưỡng thì được chấp nhận. Ở trạng thái UNKNOWN, `raw_label` và hai scores vẫn có mặt. W3 đặt ngưỡng ứng viên `0.90`, trạng thái `candidate_not_production_validated`; cần xác thực trên dữ liệu thực tế của camera triển khai.

`processing_time_ms` đo từ khi handler bắt đầu đến khi response được tạo, gồm đọc upload, validate, crop, inference và dựng kết quả; không gồm thời gian mạng.

## Lỗi

Mọi lỗi do service tạo có dạng `{"error":{"code":"...","message":"..."}}`; không có prediction giả `unknown` cho lỗi ảnh hoặc hình học. FastAPI có thể trả lỗi HTTP cấp máy chủ trước khi request tới handler, ví dụ multipart hỏng.

| HTTP | Code | Trường hợp |
|---|---|---|
| 413 | `IMAGE_TOO_LARGE` | Upload vượt giới hạn byte. |
| 413 | `SPOTS_JSON_TOO_LARGE` | JSON polygon vượt 256 KiB. |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | MIME khác JPEG/PNG. |
| 422 | `INVALID_REQUEST` | Thiếu/sai trường multipart. |
| 422 | `INVALID_CAMERA_ID` | Camera ID rỗng hoặc quá dài. |
| 422 | `INVALID_SPOTS_JSON` | JSON không đọc được. |
| 422 | `INVALID_SPOTS` | Danh sách rỗng, quá nhiều, hoặc ID không hợp lệ. |
| 422 | `DUPLICATE_SPOT_ID` | ID lặp lại. |
| 422 | `INVALID_POLYGON` | Thiếu điểm, tọa độ ngoài `[0,1]`, suy biến, tự giao hoặc quá nhỏ trên ảnh. |
| 422 | `EMPTY_IMAGE`, `INVALID_IMAGE`, `IMAGE_DIMENSIONS` | Ảnh rỗng, nội dung ảnh lỗi, hoặc kích thước không hợp lệ. |
| 503 | `MODEL_UNAVAILABLE` | Checkpoint/cấu hình lỗi hoặc model chưa load. |
| 503 | `INFERENCE_RESOURCE_ERROR` | CUDA hết bộ nhớ. |
| 500 | `INFERENCE_ERROR` | Lỗi inference khác; chi tiết nằm trong log server. |

## Chạy local

Từ root repository, sau khi cài `ai-service/requirements.txt` và đặt checkpoint cùng cấu hình W3 ở vị trí trong `configs/inference.yaml`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.service:app `
  --app-dir ai-service `
  --host 127.0.0.1 `
  --port 8001
```

`GET http://127.0.0.1:8001/ready` phải trả `status=ready`. Biến môi trường: `AI_CHECKPOINT_PATH`, `AI_THRESHOLD_CONFIG`, `AI_DEVICE` (`auto`, `cuda`, `cpu`), `AI_BATCH_SIZE`, `AI_MAX_SPOTS` (≤100), `AI_MAX_UPLOAD_BYTES`, `AI_MAX_IMAGE_PIXELS`, `AI_PORT` (dùng khi chạy `python -m src.service`; với uvicorn CLI đặt `--port` tương ứng). Path tương đối được giải từ `ai-service/`. Checkpoint SHA-256 trong W3 config phải khớp, nên không thể thay checkpoint tùy ý mà không cập nhật cấu hình đã được kiểm duyệt.

PowerShell client:

```powershell
$spots = '[{"spot_id":"P01","polygon":[[0.12,0.30],[0.20,0.30],[0.21,0.45],[0.11,0.45]]}]'
curl.exe -f -X POST http://127.0.0.1:8001/v1/infer `
  -F "camera_id=CAM01" -F "spots_json=$spots" `
  -F "image=@C:\path\to\snapshot.jpg;type=image/jpeg"
```

Python client:

```python
import json
import httpx

spots = [{"spot_id": "P01", "polygon": [[.12,.30],[.20,.30],[.21,.45],[.11,.45]]}]
with open("snapshot.jpg", "rb") as image:
    response = httpx.post("http://127.0.0.1:8001/v1/infer",
                          data={"camera_id": "CAM01", "spots_json": json.dumps(spots)},
                          files={"image": ("snapshot.jpg", image, "image/jpeg")}, timeout=30)
response.raise_for_status()
print(response.json())
```

## Trách nhiệm tích hợp

- **Khang / AI:** validate ảnh và polygon, crop W1, batch inference, softmax/UNKNOWN, phiên bản model và lỗi AI.
- **Nam / backend:** nhận snapshot, quản lý polygon và camera, gọi AI, lưu prediction/lịch sử, xử lý FULL và STALE. Chỉ ghi prediction khi HTTP 200 và `camera_id`/spot mapping khớp yêu cầu.
- **Khôi / frontend:** polygon editor, kết quả, dashboard và cảnh báo.

Cần thống nhất với Nam: quy ước normalized coordinate khi lưu polygon; thời gian chờ/retry và xử lý 503; model version trong lịch sử; xác thực camera/spot mapping; bảo mật đường gọi AI. Service hiện chưa xác thực người gọi nên chỉ bind `127.0.0.1` trong ví dụ local.
