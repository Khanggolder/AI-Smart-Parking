# Backend — AI Smart Parking

Backend dùng FastAPI, PostgreSQL, SQLAlchemy và Alembic. Nó quản lý tài khoản, bãi xe, camera, polygon, ảnh tham chiếu, snapshot, lịch sử và review. Mỗi snapshot được gửi tới AI `POST /v1/infer`; kết quả hợp lệ được lưu cùng trạng thái job. Backend không chứa trọng số model.

## Chạy local

Cần Python 3.11+ và PostgreSQL. Từ root repository, sao chép `.env.example` thành `.env` và đặt `DATABASE_URL`, `JWT_SECRET_KEY` (tối thiểu 32 byte), `AI_SERVICE_URL` và đường dẫn lưu ảnh nếu cần. Không commit `.env`. AI phải có checkpoint rc2, `/ready` trả `ready`, đúng model version `mobilenetv3-small-w2-488ed38efe01` và threshold `0.9`; `/health` chỉ kiểm tra tiến trình.

Trong PowerShell, tại thư mục `backend/`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Migration hiện gồm schema ban đầu và `20261027_02_snapshot_ai_fields`. Chạy `alembic upgrade head` trước khi dùng snapshot. Chỉ dùng database local do nhóm kiểm soát; không chạy migration trên database có dữ liệu thật khi chưa kiểm tra.

Tạo tài khoản bằng lệnh tương tác, không truyền mật khẩu trên dòng lệnh:

```powershell
.\.venv\Scripts\python.exe -m app.scripts.create_user --username admin01 --role admin
.\.venv\Scripts\python.exe -m app.scripts.create_user --username operator01 --role operator
```

Mật khẩu tối thiểu 12 ký tự, lưu dưới dạng Argon2id. Không có API đăng ký công khai. `JWT_EXPIRE_MINUTES=60` mặc định; Backend kiểm quyền từ database ở mỗi request. Admin được sửa cấu hình; Admin và Operator được đọc, gửi snapshot và xác minh dự đoán. Không có rate limit, refresh token hoặc thu hồi token trong MVP.

## API thực tế

Base URL local: `http://localhost:8000/api/v1`; Swagger ở `http://localhost:8000/docs`. Ngoài health và login, API yêu cầu `Authorization: Bearer <token>`.

| Chức năng | Endpoint chính | Quyền |
|---|---|---|
| Kiểm tra và tài khoản | `GET /health`, `POST /auth/login`, `GET /auth/me` | Public, Public, cả hai |
| Bãi xe | `GET/POST /parking-lots`, `GET/PATCH /parking-lots/{id}` | Đọc: cả hai; ghi: Admin |
| Camera | `GET/POST /cameras`, `GET/PATCH /cameras/{id}` | Đọc: cả hai; ghi: Admin |
| Ảnh tham chiếu | `PUT/GET /cameras/{id}/reference-image` | PUT: Admin; GET: cả hai |
| Polygon | `GET/POST /cameras/{id}/spots`, `PATCH/DELETE /spots/{id}` | Đọc: cả hai; ghi: Admin |
| Snapshot | `POST/GET /snapshots`, `GET /snapshots/{id}`, `GET /snapshots/{id}/image` | Cả hai |
| Review | `POST/GET /predictions/{id}/reviews` | Cả hai |

`POST /snapshots` nhận multipart `camera_id`, `captured_at` có múi giờ và ảnh JPEG/PNG; trả `202` với snapshot ID. `GET /snapshots/{id}` cho biết `queued`, `processing`, `completed` hoặc `failed`, dự đoán và summary khi hoàn tất. `GET /snapshots` hỗ trợ lọc camera, job status, thời gian và phân trang. Ảnh được trả qua endpoint có JWT, không mở thư mục lưu ảnh công khai. Frontend tự tạo CSV cho một snapshot hoàn thành; Backend chưa có `GET /reports/snapshots.csv`.

Camera cần ảnh tham chiếu và ít nhất một polygon hoạt động trước khi nhận snapshot. Ảnh snapshot phải cùng chiều rộng và cao với ảnh tham chiếu. Polygon dùng tọa độ chuẩn hóa `{x,y}`, 3–50 đỉnh, không tự cắt; mỗi camera tối đa 100 ô đang hoạt động. Đổi ảnh tham chiếu khi đã có ô hoạt động bị từ chối để tránh lệch polygon. Thay đổi cấu hình có `config_version` và có thể trả `409 CAMERA_VERSION_CONFLICT`.

## AI và trạng thái

[`app/services/ai_client.py`](app/services/ai_client.py) chuyển polygon sang `[x,y]` rồi gửi multipart `image`, `camera_id`, `spots_json` tới `/v1/infer`. Adapter kiểm camera ID, thứ tự và số lượng spot ID, nhãn, scores, confidence, threshold và model version. [`app/services/snapshot_jobs.py`](app/services/snapshot_jobs.py) ghi tất cả prediction và `completed` trong một giao dịch. AI timeout, lỗi HTTP hoặc response sai khiến job `failed`; hệ thống không tạo `unknown` giả. `unknown` từ model được giữ nguyên.

Summary dùng nhãn hiệu lực sau review: `FULL` khi mọi ô có xe, `AVAILABLE` khi có ô trống, `UNDETERMINED` khi không có ô trống nhưng còn `unknown`. `STALE` dựa trên thời điểm chụp của snapshot hoàn thành và `STALE_THRESHOLD_MINUTES` (mặc định 30). Review lưu lịch sử, không ghi đè nhãn AI gốc.

Job chạy bằng FastAPI `BackgroundTasks` trong tiến trình web. Nếu Backend dừng giữa lúc xử lý, job có thể kẹt ở `queued` hoặc `processing`; chưa có tự khôi phục hoặc retry bền vững. Khi demo, dùng một Backend worker, kiểm tra job sau mỗi lần tải ảnh và dùng snapshot mới nếu job kẹt. Không xóa dữ liệu để xử lý sự cố này.

## Kiểm thử và tài liệu

`python -m pytest -q` dùng SQLite tạm và HTTP AI mock cho phần lớn test; test PostgreSQL concurrency chỉ chạy khi cấu hình database test riêng. Test mock kiểm logic Backend, không chứng minh model thật chạy. [Báo cáo E2E W6](reports/w6_7_3_2_e2e_integration.md) ghi một lần thử với AI thật, PostgreSQL và **một ô**. Cần thử nhiều ô và luồng trình duyệt trên máy demo.

Chi tiết API xem [backend contract](../docs/api/backend-api-contract-v1.md); kiến trúc và schema hiện thực xem [SDS](../docs/design/w6_sds_backend_as_built.md). Chạy toàn hệ thống bằng [Docker Compose](../docs/DOCKER_GUIDE.md).
