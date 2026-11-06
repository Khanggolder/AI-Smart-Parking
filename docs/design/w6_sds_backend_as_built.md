# AI Smart Parking — W6 Backend SDS: kiến trúc và API as-built

**Task:** 7.4.1 — Tài liệu thiết kế Backend cập nhật theo code W2–W6.  
**Đối chiếu:** `backend/app/`, `backend/alembic/`, `backend/tests/`, `docs/design/backend-architecture-erd.md` và báo cáo E2E W6.  
**Phạm vi:** Ghi nhận thiết kế đã vận hành; sơ đồ ERD hoàn chỉnh và hồ sơ kỹ thuật tổng hợp thuộc các bước 7.4.2/7.4.3 tiếp theo.

## 1. Kiến trúc hiện thực

- **Frontend:** React/Vite trao đổi với Backend qua HTTP/JSON hoặc multipart; Bearer JWT, không tin role từ UI.
- **Backend:** FastAPI modular monolith trong `backend/app/`; `app/main.py` đăng ký các router `auth`, `parking_lots`, `cameras`, `spots`, `reference_images`, `snapshots`, `reviews`.
- **Database:** PostgreSQL + SQLAlchemy ORM, Alembic migration; SQLite in-memory dùng cho nhiều unit/API tests.
- **Ảnh:** lưu thành file riêng dưới cấu hình `REFERENCE_IMAGE_DIR`, `SNAPSHOT_IMAGE_DIR`, database giữ storage key; GET file yêu cầu JWT, `Cache-Control: private, no-store`.
- **AI:** FastAPI/PyTorch riêng, gọi qua adapter `backend/app/services/ai_client.py` tới `POST /v1/infer` (không phải `/predict` trong bản sơ đồ W1 cũ).
- **Xử lý nền:** `backend/app/services/snapshot_jobs.py`, dùng FastAPI `BackgroundTasks`; không đảm bảo khôi phục khi process crash.

## 2. Cấu trúc mã quan trọng

| Thành phần | Path | Vai trò |
|---|---|---|
| App bootstrap | `backend/app/main.py` | Khởi tạo app, middleware và router |
| Authentication | `backend/app/api/auth.py`, `api/deps.py`, `core/security.py` | Login, JWT, RBAC |
| CRUD | `backend/app/api/parking_lots.py`, `cameras.py`, `spots.py` | Quản lý cấu hình và camera version |
| Reference image | `backend/app/api/reference_images.py`, `services/reference_images.py` | Validate/upload/get private ảnh tham chiếu |
| Snapshot | `backend/app/api/snapshots.py` | Upload, history, snapshot detail, private image |
| AI adapter & worker | `backend/app/services/ai_client.py`, `snapshot_jobs.py` | Chuẩn hóa request, validate AI response, lưu job/predictions |
| Review | `backend/app/api/reviews.py`, `schemas/reviews.py` | Accept/Correct và history, audit, version conflict |
| ORM | `backend/app/models/entities.py` | Tám thực thể và ràng buộc |
| Tests | `backend/tests/test_*.py` | API, schema, migration, review, PostgreSQL concurrency |

## 3. API contract (base `/api/v1`)

| Method | Endpoint | Quyền | Mục đích |
|---|---|---|---|
| POST | `/auth/login` | Public | JWT đăng nhập |
| GET | `/auth/me` | Admin / Operator | Thông tin user |
| GET/POST/PATCH | `/parking-lots` + `/{lot_id}` | GET hai role; ghi Admin | CRUD bãi |
| GET/POST/PATCH | `/cameras` + `/{camera_id}` | GET hai role; ghi Admin | CRUD camera |
| PUT/GET | `/cameras/{camera_id}/reference-image` | PUT Admin; GET hai role | Ảnh tham chiếu bảo vệ |
| GET/POST | `/cameras/{camera_id}/spots` | GET hai role; POST Admin | Danh sách/tạo polygon |
| PATCH/DELETE | `/spots/{spot_id}` | Admin | Sửa/soft deactivate polygon |
| POST | `/snapshots` | Admin / Operator | Multipart upload; HTTP 202 + snapshot ID |
| GET | `/snapshots` | Admin / Operator | Filter camera/status/from/to; limit/offset |
| GET | `/snapshots/{snapshot_id}` | Admin / Operator | Job, AI result, effective labels, summary, freshness |
| GET | `/snapshots/{snapshot_id}/image` | Admin / Operator | File ảnh private |
| POST | `/predictions/{prediction_id}/reviews` | Admin / Operator | Accept/Correct; HTTP 201, hoặc 409 conflict |
| GET | `/predictions/{prediction_id}/reviews` | Admin / Operator | Lịch sử review theo revision |

**Không tuyên bố đã có:** `/reports/snapshots.csv` chưa có router triển khai xác nhận trong code nguồn đã kiểm tra. Bản contract W1 có thể mô tả endpoint tương lai; cần cập nhật trạng thái.

## 4. Snapshot lifecycle và transaction

1. POST validate camera, reference image, active polygons (1–100), ảnh giải mã hợp lệ và cùng resolution, UTC timestamp.
2. Copy ID/mã/polygon của các spot và `camera_config_version` tại thời điểm upload; lưu file + `Snapshot(job_status=queued)`.
3. BackgroundTask chuyển `processing`, gửi multipart tới AI (`camera_id`, `spots_json`, `image`).
4. Adapter validate spot IDs thứ tự, raw/final label, confidence, scores, threshold, model_version và thời gian inference. Không tạo unknown giả khi AI báo lỗi.
5. Ghi toàn bộ `SpotPrediction` và trạng thái `completed` cùng transaction; lỗi chuyển `failed` với `error_code`.
6. GET detail truy xuất latest SpotReview theo revision, tính `effective_label`; aggregate FULL chỉ khi có ít nhất một ô và tất cả occupied.

**Quy tắc summary:** `total = empty + occupied + unknown`; `occupancy_rate = occupied / total × 100` nếu total > 0; ưu tiên AVAILABLE khi có empty, UNDETERMINED nếu không empty nhưng có unknown; FULL chỉ khi tất cả occupied.

## 5. Review và concurrency

- POST body: `action` (`accept|correct`), `expected_revision >= 0`, `verified_label` khi `correct`, `reason` bắt buộc khi `correct`.
- `accept` xác minh đúng nhãn AI gốc; `correct` dùng nhãn khác AI gốc và lý do rõ ràng.
- Dùng `SELECT ... FOR UPDATE` trên prediction để tuần tự hóa review đồng thời trong PostgreSQL; so sánh `expected_revision` với max revision; thêm review với unique `(spot_prediction_id, revision)`.
- Thêm `AuditLog(action='prediction.review.accept|correct')` trong cùng DB transaction; giữ `SpotPrediction.predicted_label` bất biến.
- GET history trả reviewer/timestamp/revision; tại W5 action được suy ra từ so sánh verified và AI gốc, chưa có cột `action` trong bảng `spot_reviews`.

## 6. Mô hình dữ liệu (tóm tắt, chi tiết thuộc 7.4.2)

- `User` (1) → (n) `SpotReview`, (n) `AuditLog`
- `ParkingLot` (1) → (n) `Camera`
- `Camera` (1) → (n) `ParkingSpot`, (n) `Snapshot`
- `Snapshot` (1) → (n) `SpotPrediction`
- `ParkingSpot` (1) → (n) `SpotPrediction`
- `SpotPrediction` (1) → (n) `SpotReview`

Chính sách khóa ngoại RESTRICT bảo vệ liên kết lịch sử; có unique/constraint cho `username`, `camera_id+spot_code`, `snapshot_id+parking_spot_id`, `spot_prediction_id+revision`.

## 7. Kiểm thử và bằng chứng

- `backend/reports/w6_7_3_1_api_regression.md`: hồi quy Auth, CRUD, upload, snapshot history, reviews (người thực hiện báo PASS).
- `backend/reports/w6_7_3_2_e2e_integration.md`: E2E AI thật với model `mobilenetv3-small-w2-488ed38efe01`, CPU, ảnh 724×738, 1 spot, inference 44.077 ms; POST 202; persisted Snapshot/Prediction/Audit (theo output kiểm thử người thực hiện).
- `backend/tests/test_reviews_pg_concurrency.py`: 2 requests đồng thời trên PostgreSQL test riêng, đã được người thực hiện báo PASS ở W5. Không chạy mặc định khi thiếu `W5_TEST_POSTGRES_URL`.

## 8. Giới hạn, rủi ro và hạng mục chưa đáp ứng

- `BackgroundTasks` không bền vững khi restart; chưa có persistent job queue, retries, idempotency và job recovery.
- Không xác nhận tính năng CSV download; đây là điểm thiếu so với FR-12 trong SRS.
- `is_stale` chỉ áp dụng snapshot được GET; dashboard freshness mới nhất của camera là nhiệm vụ bổ sung.
- Chưa chứng minh benchmark 100 ô thực tế hoặc độ chính xác camera mới qua E2E một ảnh tham chiếu.
- Mọi `.env`, secret, password, ảnh nhạy cảm và checkpoint model phải ở ngoài Git.

## 9. Đề nghị cập nhật tài liệu nhóm

- Đồng bộ bản SRS Word với bảng FR ở file W6 này sau khi leader duyệt.
- Cập nhật API Contract v1 theo endpoint thực tế (`/v1/infer`, review history, private image, CSV chưa triển khai).
- Cập nhật sơ đồ ERD/kiến trúc ở task 7.4.2; tránh để sơ đồ W1 còn ghi `/predict` và pipeline W2 chưa chạy.
