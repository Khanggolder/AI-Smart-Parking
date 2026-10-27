# AI Smart Parking — REST API Contract v1 (W1 / 2.2)

**Trạng thái:** Contract W1 chốt để triển khai. W2 đã hiện thực Health, Auth và CRUD Parking Lots/Cameras; các endpoint khác ở bảng bên dưới vẫn đang phát triển.  
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

## 4. Backend ↔ AI Service contract (W4 hiện thực)

**API thực tế**: `POST {AI_SERVICE_URL}/v1/infer`. Thay thế mô tả cũ
`/predict`; đây không phải đổi endpoint trên AI Service. Backend gửi
`multipart/form-data`:

- `image`: ảnh snapshot JPEG/PNG gốc (<= 10MiB theo mặc định).
- `camera_id`: UUID camera dạng string, chỉ được service AI echo.
- `spots_json`: chuỗi JSON array; mỗi spot dùng UUID cố định `spot_id` và
  `polygon` là danh sách 3–50 cặp `[x, y]` normalized. Backend chuyển từ
  danh sách các điểm `{x,y}` đã lưu trong PostgreSQL. Giữ nguyên thứ tự.

**AI trả HTTP 200** với `camera_id`, `model_version`, `threshold`,
`processing_time_ms` và mảng `predictions`. Mỗi dự đoán có `spot_id`,
`raw_label` (empty/occupied), `label` (empty/occupied/unknown), `confidence`,
`scores` gồm empty/occupied. Backend kiểm tra đầy đủ, hữu hạn, nhãn đúng
với ngưỡng, `spot_id` đủ số lượng và thứ tự. Mọi kết quả không khớp bị hủy;
không được tự tạo `unknown` để thay lỗi mạng/model.

`AI_SERVICE_URL=http://127.0.0.1:8001` trong local. `/ready=200` xác nhận
model sẵn sàng, còn `/health=200` chỉ là tiến trình sống.
Gói bàn giao là `v0.1.0-rc2`, model version
`mobilenetv3-small-w2-488ed38efe01`, threshold ứng viên 0.90.
Checkpoint phải do AI service tải; Backend chỉ gọi HTTP và **không có nhãn thật**.

API Backend `POST /snapshots` nhận `camera_id`, `captured_at` với timezone và
`image` trong multipart, trả `202 {id,camera_id,captured_at,
 camera_config_version,job_status:"queued"}`. Phải có ảnh tham chiếu thật,
1–100 spot active, snapshot cùng kích thước ảnh tham chiếu. Cấu hình polygon
được sao chép bất biến vào `snapshots.spots_at_capture` ở thời điểm nhận ảnh.
Một tác vụ nền thực hiện `queued -> processing -> completed/failed`.

`GET /snapshots/{id}` trả `error_code` khi failed; khi completed trả
`summary`, `predictions` với spot code/polygon gốc, label/raw/scores/confidence,
model_version và threshold. `GET /snapshots/{id}/image` trả file có JWT.
`GET /snapshots` có filter camera/status/thời gian và phân trang.
`effective_label` hiện bằng `predicted_label`; review append-only triển khai sau.

**W4 MVP limitation:** BackgroundTasks là in-process, chưa bền qua restart;
cần durable queue, recovery, retry giới hạn và idempotency trước production.
`is_stale` của snapshot completed phản ánh tuổi của ảnh đó; dashboard cuối
cùng sẽ dùng snapshot completed mới nhất của từng camera, không biến lỗi AI
thành trạng thái `unknown`.

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

## 8. W2 – Hợp đồng hiện thực CRUD Parking Lots và Cameras (3.2)

**Phân quyền:** Tất cả endpoint phần này yêu cầu Bearer JWT. Admin/Operator xem được; chỉ Admin được POST/PATCH. Operator ghi trả 403; không có token trả 401.

**GET danh sách:**
- `GET /parking-lots?limit=20&offset=0`
- `GET /cameras?parking_lot_id=<uuid>&limit=20&offset=0`; bộ lọc `parking_lot_id` không bắt buộc.
- Trả về `{"items":[],"total":0,"limit":20,"offset":0}`. Giới hạn `1 <= limit <= 100`; `offset >= 0`. Màn hình Frontend đã có hỗ trợ lấy `items`.

**Parking Lots:**
- `POST /parking-lots`: `{"name":"Bãi A","description":"Khu A"}` → 201, trả `{id,name,description,created_at}`.
- `GET /parking-lots/{lot_id}` → 200 hoặc 404.
- `PATCH /parking-lots/{lot_id}`: gửi một hoặc cả hai trường `name`, `description`; `description:null` để xóa mô tả; `name` không được rỗng/null. Trả 200 hoặc 404.

**Cameras:**
- `POST /cameras`: `{"parking_lot_id":"<uuid>","name":"CAM-01"}` → 201, trả `{id,parking_lot_id,name,reference_image_path,reference_width,reference_height,config_version}`; bãi không tồn tại → 404.
- `GET /cameras/{camera_id}` → 200 hoặc 404.
- `PATCH /cameras/{camera_id}`: `{ "name":"CAM-02", "expected_camera_config_version":1 }` → 200, tăng `config_version` khi đổi tên; phiên bản kỳ vọng là **tùy chọn** (để tương thích Frontend hiện tại), nhưng nên gửi để bảo vệ cập nhật đồng thời. Trùng/sai phiên bản → 409 `CAMERA_VERSION_CONFLICT`. Gửi tên giữ nguyên không tăng version.
- Không nhận đổi `parking_lot_id`, đường dẫn ảnh hay kích thước tham chiếu trong PATCH. API riêng `PUT /cameras/{id}/reference-image` sẽ làm ở bước tiếp theo.

**Validation:** Tên trim whitespace, dài 1–160; mô tả tối đa 1000 ký tự; field không hợp lệ/không cho phép → 422. UUID không hợp lệ → 422. Không có endpoint xóa thật ở W2 vì cần bảo toàn lịch sử.

**Audit:** Mỗi thao tác tạo hoặc cập nhật có thay đổi đều ghi `audit_logs` cùng transaction với dữ liệu nghiệp vụ; không phải tạo migration mới vì schema đã đủ.

**CORS development:** Mặc định cho phép hai React origin `http://localhost:5173` và `http://127.0.0.1:5173`. Có thể cấu hình `CORS_ORIGINS` trong `.env`; không mở wildcard ở môi trường triển khai.


## 9. W3 phase 1 — Parking Spot Polygon API (FR-03 / FR-04)

These endpoints are now implemented in W3 Backend; remaining W3 image upload
and Frontend editor integration are tracked separately.

- `GET /cameras/{camera_id}/spots?include_inactive=false`: Admin/Operator,
  `200 {"items":[],"total":0,"camera_config_version":1}`. `include_inactive=true`
  also returns soft-deactivated spots.
- `POST /cameras/{camera_id}/spots`: Admin, requires `spot_code`, `polygon` and
  **required** `expected_camera_config_version` (integer >= 1). `201` returns
  `{id,camera_id,spot_code,polygon,is_active,camera_config_version}`.
- `PATCH /spots/{spot_id}`: Admin, requires `expected_camera_config_version`
  and either `spot_code` and/or `polygon`; no change → `200` with same version.
- `DELETE /spots/{spot_id}?expected_camera_config_version=N`: Admin, `204`
  with no response body. Soft-deletes (`is_active=false`) without removing
  history or releasing the spot code.

`polygon` uses a list of `{x,y}` with 3–50 **distinct** vertices. Every x/y is
finite and in `[0,1]`. Degenerate, self-crossing or self-touching polygons are
rejected `422`. `spot_code` is trimmed, uppercased and must be unique per camera
(including deactivated spots); duplicates → `409 SPOT_CODE_CONFLICT`.
There may be at most 100 active spots per camera, matching the AI service limit.

Changes require the caller's *current* camera version: `409 CAMERA_VERSION_CONFLICT`
if another write won. Each successful actual write increments `Camera.config_version`
and writes `audit_logs` in the same transaction. `401` no/invalid token;
`403` Operator write; `404` missing spot/camera; `409 SPOT_INACTIVE` when trying
to change an already disabled spot.

W3 phase 1 validates polygon geometry but **does not implement or enforce**
reference-image upload/dimensions. W1 UC-01's prerequisite (valid camera reference
image) remains an integration requirement and is not met by this API alone.
`PUT /cameras/{camera_id}/reference-image` will be implemented separately before
relying on polygon coordinates for real snapshots. AI adapter must map stored
`{x,y}` to `[x,y]` when calling the existing `POST /v1/infer` service.


## 10. W3 phase 2 — Camera reference-image upload and protected read

- `PUT /cameras/{camera_id}/reference-image` — **Admin**, `multipart/form-data`:
  required `image` (JPEG/PNG bytes) and required integer
  `expected_camera_config_version` (>= 1).
- Returns `200` `CameraOut`: `{id,parking_lot_id,name,reference_image_path,
  reference_width,reference_height,config_version}`.
- `GET /cameras/{camera_id}/reference-image` — **Admin/Operator**,
  returns `200` binary `image/jpeg` or `image/png` with `private, no-store`.
  There is no unauthenticated static URL.
- `reference_image_path` is an opaque relative storage key, **not** an
  absolute path or publicly accessible URL. Filenames are random. Bytes are
  written under `REFERENCE_IMAGE_DIR` (default: `backend/storage/reference-images`)
  and excluded from Git.
- Files are checked for actual format, decoding, size (`UPLOAD_MAX_MB`,
  default 10 MiB) and dimensions (max 20 million pixels).
  Unsupported or mismatched MIME → 415; malformed/truncated image → 422;
  excess bytes → 413.
- The camera's `config_version` is updated via optimistic conditional UPDATE.
  Stale version → `409 CAMERA_VERSION_CONFLICT`; upload refuses while any
  **active** parking spots exist → `409 ACTIVE_SPOTS_EXIST`. Deactivate/reconfigure
  old spots before replacing the frame so old polygon geometry is not silently
  reused on a different reference image.
- A successful upload commits camera dimensions, relative image key,
  incremented version and audit event together. If DB commit fails, the newly
  stored image is cleaned up; old immutable reference files remain for now.
- Missing camera/image → 404; unauthenticated → 401; Operator PUT → 403.
  No migration needed because `cameras` already has the three reference fields.

**Boundary:** The current React `/polygon-editor` remains a placeholder;
W3 upload/read APIs do not themselves provide the drawing UI. W4 snapshot/AI
must still validate a camera reference frame and map `{x,y}` vertices to
`[x,y]` for the AI service's actual `POST /v1/infer` endpoint.
