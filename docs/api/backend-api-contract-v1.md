# AI Smart Parking — REST API Contract v1 (W1 / 2.2)

**Trạng thái:** Thiết kế **chốt để triển khai** theo SRS/WBS; **chưa có API đang chạy**.  
**Base URL:** `http://localhost:8000/api/v1` trong môi trường local.  
**Data format:** JSON UTF-8, ngoại trừ upload snapshot (multipart) và xuất CSV (`text/csv`).

## 1. Nguyên tắc chung

- JWT bearer: `Authorization: Bearer <access_token>` cho tất cả endpoint ngoài login và health check.
- UUID dạng chuỗi. `snake_case` cho field trong JSON. Timestamp ISO 8601 có múi giờ, server lưu UTC.
- Danh sách phân trang với `limit=20` (max 100) và `offset=0`.
- Bản v1 chỉ quản lý nghiệp vụ MVP 1 bãi, 1 camera, nhưng thiết kế schema hỗ trợ quan hệ lot/camera mở rộng.
- Admin được xem và xử lý như Operator; Operator không thay đổi cấu hình.
- Quy trình suy luận async: POST snapshot trả `202` và ID, UI polling GET; không trả prediction giả ngay khi upload.

## 2. Bảng endpoint

| Method | Endpoint | Role | Success | Yêu cầu |
|---|---|---|---|---|
| GET | `/health` | Public | 200 | kiểm tra service |
| POST | `/auth/login` | Public | 200 | token từ username/password |
| GET | `/auth/me` | Admin/Operator | 200 | người dùng hiện tại |
| GET | `/parking-lots` | Admin/Operator | 200 | danh sách bãi |
| POST | `/parking-lots` | Admin | 201 | tạo bãi |
| GET | `/parking-lots/{lot_id}` | Admin/Operator | 200 | xem bãi |
| PATCH | `/parking-lots/{lot_id}` | Admin | 200 | sửa bãi |
| GET | `/cameras?parking_lot_id=...` | Admin/Operator | 200 | danh sách camera |
| POST | `/cameras` | Admin | 201 | tạo camera, lưu ảnh tham chiếu qua bước upload riêng khi triển khai |
| GET | `/cameras/{camera_id}` | Admin/Operator | 200 | cấu hình camera |
| PATCH | `/cameras/{camera_id}` | Admin | 200 | cập nhật camera/phiên bản |
| GET | `/cameras/{camera_id}/spots` | Admin/Operator | 200 | danh sách polygon |
| POST | `/cameras/{camera_id}/spots` | Admin | 201 | tạo spot, kiểm tra polygon |
| PATCH | `/spots/{spot_id}` | Admin | 200 | cập nhật spot |
| DELETE | `/spots/{spot_id}` | Admin | 204 | ngừng kích hoạt spot; giữ lịch sử snapshot |
| POST | `/snapshots` | Admin/Operator | 202 | upload snapshot và tạo job |
| GET | `/snapshots` | Admin/Operator | 200 | lọc / phân trang lịch sử |
| GET | `/snapshots/{snapshot_id}` | Admin/Operator | 200 | trạng thái job, dự đoán, thống kê |
| POST | `/predictions/{prediction_id}/reviews` | Admin/Operator | 201 | chấp nhận/sửa nhãn append-only |
| GET | `/reports/snapshots.csv` | Admin/Operator | 200 | xuất lịch sử theo filter |

**Chính sách DELETE:** Không hard-delete đối tượng camera/spot nếu có lịch sử; `DELETE /spots/{id}` là soft delete `is_active=false`. Nếu cần xóa camera/bãi sau này phải định nghĩa riêng để không phá liên kết lịch sử.

**Quản lý ảnh tham chiếu:** Khi triển khai W2, ưu tiên bổ sung `PUT /cameras/{camera_id}/reference-image` (multipart) để ràng buộc metadata kích thước/phiên bản camera, thay vì nhúng base64 vào JSON. Đây là endpoint đã chọn trong contract dù chưa nằm trong bảng CRUD cơ bản trên.

## 3. Các payload chính

### 3.1 Đăng nhập

`POST /auth/login` (JSON)

```json
{"username":"operator01", "password":"<user-supplied-password>"}
```

`200`:

```json
{"access_token":"<jwt>", "token_type":"bearer", "expires_in":3600}
```

### 3.2 Tạo spot

`POST /cameras/5c9dce78-7b7e-4503-8498-523220028b6e/spots`

```json
{
  "spot_code":"P01",
  "polygon":[
    {"x":0.10,"y":0.20},
    {"x":0.25,"y":0.20},
    {"x":0.25,"y":0.40},
    {"x":0.10,"y":0.40}
  ],
  "expected_camera_config_version":1
}
```

`201`:

```json
{
  "id":"c5c646c3-e985-4d3c-a12f-191b69e6b9da",
  "camera_id":"5c9dce78-7b7e-4503-8498-523220028b6e",
  "spot_code":"P01",
  "polygon":[{"x":0.10,"y":0.20},{"x":0.25,"y":0.20},{"x":0.25,"y":0.40},{"x":0.10,"y":0.40}],
  "camera_config_version":2
}
```

Polygon không hợp lệ → 422; `spot_code` trùng → 409; `expected_camera_config_version` không khớp → 409; Operator → 403.

### 3.3 Upload snapshot

`POST /snapshots` với `multipart/form-data`:

| Form key | Loại | Bắt buộc |
|---|---|---|
| `camera_id` | UUID string | Có |
| `captured_at` | ISO 8601 timestamp | Có |
| `image` | binary JPEG/PNG | Có |

Ví dụ `202`:

```json
{
  "id":"06dfd72a-f8a4-47d5-9463-9c862401fa06",
  "camera_id":"5c9dce78-7b7e-4503-8498-523220028b6e",
  "job_status":"queued",
  "camera_config_version":2,
  "captured_at":"2026-10-25T03:00:00+07:00"
}
```

Giới hạn `UPLOAD_MAX_MB=10` theo `.env.example`. Không chấp nhận file chỉ đổi đuôi; phải kiểm tra nội dung ảnh thực tế. Khi AI offline, job chuyển sang `failed`, lịch sử thành công trước vẫn xem được.

### 3.4 GET snapshot đã hoàn tất

`GET /snapshots/06dfd72a-f8a4-47d5-9463-9c862401fa06`

```json
{
  "id":"06dfd72a-f8a4-47d5-9463-9c862401fa06",
  "camera_id":"5c9dce78-7b7e-4503-8498-523220028b6e",
  "captured_at":"2026-10-24T20:00:00Z",
  "job_status":"completed",
  "camera_config_version":2,
  "summary":{
    "total":3,"empty":1,"occupied":1,"unknown":1,
    "occupancy_rate":33.3,"full":false,"status":"AVAILABLE"
  },
  "predictions":[
    {"id":"a0e81783-c9da-4f26-94df-c7989d78e0ca","spot_code":"P01","predicted_label":"empty","effective_label":"empty","confidence":0.94,"model_version":"baseline-v1","polygon":[{"x":0.1,"y":0.2},{"x":0.25,"y":0.2},{"x":0.25,"y":0.4}]},
    {"id":"4d93f713-fde8-4f59-a9e6-8a6ae69c9503","spot_code":"P02","predicted_label":"occupied","effective_label":"occupied","confidence":0.96,"model_version":"baseline-v1","polygon":[{"x":0.3,"y":0.2},{"x":0.45,"y":0.2},{"x":0.45,"y":0.4}]},
    {"id":"c219d5f9-21ab-4b73-8c5b-8ae6498f7a49","spot_code":"P03","predicted_label":"unknown","effective_label":"unknown","confidence":0.42,"model_version":"baseline-v1","polygon":[{"x":0.5,"y":0.2},{"x":0.65,"y":0.2},{"x":0.65,"y":0.4}]}
  ]
}
```

`summary` là tổng từ dự đoán gốc khi snapshot hoàn tất; để phân biệt sau review, Backend có thể trả thêm `reviewed_summary` tính từ nhãn hiệu lực, **không** được ghi đè hoặc đổi ngầm `summary` gốc. Trạng thái `STALE` là trạng thái **độ mới dữ liệu** riêng (`is_stale`), không nhập chung vào `summary.status` (FULL/AVAILABLE/UNDETERMINED/NO_SPOTS).

### 3.5 Review nhãn

`POST /predictions/{prediction_id}/reviews`

```json
{"verified_label":"occupied", "reason":"Kiểm tra lại ảnh", "expected_revision":0}
```

`201`:

```json
{"id":"0ad65d70-e68a-450d-a81e-cf014cf460fd","prediction_id":"c219d5f9-21ab-4b73-8c5b-8ae6498f7a49","verified_label":"occupied","revision":1,"reviewer_id":"a0d591dd-5da5-4251-95d8-c1b06d6703ac","changed_at":"2026-10-24T20:12:00Z"}
```

### 3.6 Lọc lịch sử, báo cáo

`GET /snapshots?camera_id=<uuid>&from=2026-10-01T00:00:00Z&to=2026-10-31T23:59:59Z&job_status=completed&limit=20&offset=0`

```json
{"items":[],"total":0,"limit":20,"offset":0}
```

CSV phải sử dụng cùng bộ lọc để không sai số với giao diện, định dạng UTF-8; không đưa đường dẫn nội bộ hoặc secret vào CSV.

## 4. Backend ↔ AI Service contract

**Endpoint nội bộ dự kiến:** `POST {AI_SERVICE_URL}/predict` (multipart gồm ảnh + JSON metadata). Chuẩn hóa tọa độ do Backend thực hiện; AI trả spot IDs không được thay đổi.

Metadata JSON dạng:

```json
{
  "snapshot_id":"06dfd72a-f8a4-47d5-9463-9c862401fa06",
  "camera_id":"5c9dce78-7b7e-4503-8498-523220028b6e",
  "camera_config_version":2,
  "spots":[{"spot_id":"c5c646c3-e985-4d3c-a12f-191b69e6b9da","polygon":[{"x":0.1,"y":0.2},{"x":0.25,"y":0.2},{"x":0.25,"y":0.4}]}]
}
```

AI trả:

```json
{
  "model_version":"baseline-v1",
  "inference_ms":1240,
  "predictions":[{"spot_id":"c5c646c3-e985-4d3c-a12f-191b69e6b9da","label":"occupied","confidence":0.95}]
}
```

Backend kiểm tra `spot_id` thuộc camera/snapshot, không trùng, đủ số lượng; `confidence ∈ [0,1]`, nhãn hợp lệ, `model_version` không rỗng. Response thiếu/không hợp lệ → job `failed`; có thể bổ sung retry nhưng không lưu kết quả nửa vời. **Bộ dữ liệu gán nhãn không đi trong inference request.**

## 5. Error format và status code

```json
{"error":{"code":"SPOT_CODE_CONFLICT","message":"Mã ô đỗ đã tồn tại trong camera","details":{}}}
```

| HTTP | Trường hợp |
|---|---|
| 400 | Bad request về nghiệp vụ không thuộc lỗi schema |
| 401 | Token thiếu/sai/hết hạn |
| 403 | Đủ xác thực nhưng thiếu quyền |
| 404 | Không tìm thấy tài nguyên |
| 409 | Trùng mã, xung đột chỉnh sửa, version conflict |
| 413 | File lớn hơn giới hạn cấu hình |
| 415 | MIME/type ảnh không hỗ trợ |
| 422 | Schema/đa giác/ảnh không giải mã hợp lệ |
| 503 | AI service không sẵn sàng ở các endpoint gọi AI đồng bộ (nếu có); POST snapshot async vẫn 202 sau đó job FAILED |

FastAPI trả 422 mặc định cho lỗi schema; khi hiện thực cần chuẩn hóa sang cấu trúc `error` cho thống nhất, hoặc cập nhật rõ contract nếu giữ định dạng mặc định. Không thay đổi format một cách âm thầm.

## 6. Quy tắc thống kê và cảnh báo

`total = empty + occupied + unknown`; `occupancy_rate = occupied / total * 100` nếu total>0; không có ô thì `null`. 
- `total = 0` → `NO_SPOTS`, `full=false`.
- `empty > 0` → `AVAILABLE`, `full=false`.
- `empty = 0`, `unknown > 0` → `UNDETERMINED`, `full=false`.
- `total > 0`, `empty = 0`, `unknown = 0` → `FULL`, `full=true`.
- STALE được tính từ snapshot `completed` gần nhất và `STALE_THRESHOLD_MINUTES`; trả `is_stale` độc lập.

## 7. Chính sách thay đổi API

- Tất cả API đã chốt trong tài liệu này là cơ sở triển khai; không cần họp riêng cho mỗi endpoint.
- Nếu thay đổi breaking change, cập nhật file này trong **cùng PR** với code, đánh dấu phiên bản hoặc mô tả migration.
- Frontend/AI xem tài liệu này trong repo, có thể tích hợp theo contract mà không cần chờ phê duyệt lại W1.
- Mã lỗi, yêu cầu role và dữ liệu demo phải có integration test. Không gọi mock AI là inference thật.
