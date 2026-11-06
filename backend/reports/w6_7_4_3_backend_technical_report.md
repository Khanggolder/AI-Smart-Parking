# AI Smart Parking — W6 Backend Technical Report (As-built)

**Task:** 7.4.3 — Tổng hợp hồ sơ kỹ thuật Backend và minh chứng kiểm thử.  
**Ngày tổng hợp (UTC):** 2026-11-06 03:51:27 UTC  
**Nhánh local:** `feature/backend-w6-regression-release` — commit `1d773d6`  
**Nguồn:** Mã Backend, tài liệu as-built 7.4.1/7.4.2, báo cáo test 7.3.1/7.3.2 và lần chạy regression cuối 7.3.3.  
**Phạm vi:** Dự án AI Smart Parking; 1 camera cố định, snapshot JPEG/PNG, tối đa 100 polygon theo ràng buộc API.

## 1. Tóm tắt kết quả

| Mốc | Bằng chứng | Kết quả |
|---|---|---|
| 7.3.1 — Backend API regression | [`w6_7_3_1_api_regression.md`](w6_7_3_1_api_regression.md) | **PASS** (báo cáo đã đọc) |
| 7.3.2 — AI rc2 → Backend → PostgreSQL E2E | [`w6_7_3_2_e2e_integration.md`](w6_7_3_2_e2e_integration.md) | **PASS** (báo cáo đã đọc) |
| 7.3.3 — Final regression | [`w6_7_3_3_final_regression.md`](w6_7_3_3_final_regression.md) | **PASS** (chạy lại tại thời điểm tạo báo cáo) |
| 7.4.1 — SRS/SDS as-built | `docs/requirements/w6_srs_backend_as_built.md`, `docs/design/w6_sds_backend_as_built.md` | Đã có file local |
| 7.4.2 — ERD & Architecture | `docs/design/w6_erd_backend_as_built.md`, `docs/design/w6_architecture_backend_as_built.md` | Đã có file local |

**Giới hạn phạm vi:** Kết quả E2E hiện xác minh luồng tích hợp thật qua ảnh tham chiếu của camera và 1 polygon; **không phải đánh giá accuracy AI trên ảnh độc lập**, không chứng minh tải 100 ô hay độ tin cậy production. Chỉ báo cáo Backend, chưa nghiệm thu trải nghiệm Frontend end-to-end.

## 2. Kiến trúc thực tế

- **FastAPI backend** (mô hình modular monolith) cung cấp `/api/v1` với login JWT, RBAC Admin/Operator, CRUD bãi/camera/spot, upload ảnh tham chiếu, snapshot, lịch sử và review.
- **PostgreSQL** lưu metadata 8 thực thể `users`, `parking_lots`, `cameras`, `parking_spots`, `snapshots`, `spot_predictions`, `spot_reviews`, `audit_logs`; SQLAlchemy ORM và Alembic quản lý schema.
- **File storage private** lưu JPEG/PNG bên ngoài thư mục public. DB giữ storage key, GET ảnh yêu cầu JWT.
- **AI inference service** độc lập (checkpoint `v0.1.0-rc2`, MobileNetV3-Small) nhận `POST /v1/infer`; `backend/app/services/ai_client.py` chuyển đổi request và kiểm tra response.
- **BackgroundTasks** xử lý job trong tiến trình Backend: `queued → processing → completed/failed`. Khi thành công, ghi toàn bộ predictions và chuyển trạng thái completed trong một transaction.

Tài liệu chi tiết: [`w6_architecture_backend_as_built.md`](../../docs/design/w6_architecture_backend_as_built.md) và [`w6_erd_backend_as_built.md`](../../docs/design/w6_erd_backend_as_built.md).

## 3. Chức năng Backend đã triển khai

| Nhóm chức năng | API / Cơ chế |
|---|---|
| Auth + RBAC | `POST /auth/login`, `GET /auth/me`, bảo vệ Admin/Operator |
| Parking & Camera | CRUD có phân quyền, camera config version |
| Parking polygons | GET/POST camera spots, PATCH/DELETE spots, kiểm tra hình học và version conflict |
| Reference image | PUT/GET ảnh tham chiếu private; giới hạn kích thước/định dạng |
| Snapshot & inference | POST multipart `/snapshots` (202), worker gọi AI thật |
| History & kết quả | GET `/snapshots`, GET `/snapshots/{id}`, GET ảnh snapshot private |
| Review | POST/GET `/predictions/{id}/reviews`, revision conflict 409, audit, effective label |
| Summary | `total`, `empty`, `occupied`, `unknown`, `occupancy_rate`, `FULL`, `is_stale` trên snapshot hoàn thành |

`predicted_label` được giữ nguyên; `effective_label` đến từ latest review. Khi `unknown`, hệ thống không tự xem là ô trống; FULL chỉ khi mọi ô occupied và tổng > 0.

## 4. Minh chứng kiểm thử W6

### 4.1. API Regression — Task 7.3.1

Nguồn [`w6_7_3_1_api_regression.md`](w6_7_3_1_api_regression.md):

```text
Outcome: PASS (details in original 7.3.1 report)
```

Các nhóm test được chạy theo báo cáo: Auth/RBAC, CRUD, polygon, upload, snapshot/history/review, health, schema và migration. Concurrency PostgreSQL chạy riêng ở W5, không bao gồm trong bộ regression mặc định.

### 4.2. Real AI E2E — Task 7.3.2

Nguồn [`w6_7_3_2_e2e_integration.md`](w6_7_3_2_e2e_integration.md). Những bước xác minh thực tế được ghi trong báo cáo:

- PASS: Backend /api/v1/health
- PASS: Real AI /ready (model=mobilenetv3-small-w2-488ed38efe01, device=cpu)
- PASS: JWT login & /auth/me (role=admin)
- PASS: Camera selected (camera_id=dbfbc57f-eb13-4899-9d22-92a331510e54, active_spots=1, reference=724x738)
- PASS: Image loaded (bytes=586815, mode=existing camera reference image (integration only, not model accuracy))
- PASS: POST /snapshots (HTTP 202, snapshot_id=138a27a1-c9fe-4a74-a838-863f4b913880)
- PASS: Real AI inference completed (model=mobilenetv3-small-w2-488ed38efe01, predictions=1, time_ms=44.077)
- PASS: Summary (empty=0, occupied=1, unknown=0, status=FULL, full=True)
- PASS: Private snapshot GET image matches uploaded image SHA-256
- PASS: Snapshot appears in GET history
- PASS: W5 Review History returns [] for new prediction
- PASS: PostgreSQL persisted 1 Snapshot + 1 SpotPredictions + 1 snapshot audit log(s)
- PASS: W6 7.3.2 REAL AI E2E verification completed

Tại thời điểm test, snapshot và prediction đã được tạo trong **database local được cấu hình**. Kết quả `FULL`/`occupied` của riêng ảnh test không xác nhận độ chính xác mô hình trên ảnh khác.

### 4.3. Final Regression — Task 7.3.3

Bộ pytest Backend được chạy lại khi tạo tài liệu này; đầu ra lưu nguyên vẹn tại [`w6_7_3_3_final_regression.md`](w6_7_3_3_final_regression.md).

```text
89 passed, 1 skipped, 1 warning in 11.70s
```

## 5. Truy vết tài liệu — mã nguồn — test

| Tài liệu | File đối chiếu |
|---|---|
| SRS as-built | [`w6_srs_backend_as_built.md`](../../docs/requirements/w6_srs_backend_as_built.md) |
| SDS as-built | [`w6_sds_backend_as_built.md`](../../docs/design/w6_sds_backend_as_built.md) |
| ERD | [`w6_erd_backend_as_built.md`](../../docs/design/w6_erd_backend_as_built.md) |
| Architecture/Sequence | [`w6_architecture_backend_as_built.md`](../../docs/design/w6_architecture_backend_as_built.md) |
| Backend source | `backend/app/api/`, `backend/app/services/`, `backend/app/models/entities.py` |
| Unit & API tests | `backend/tests/` |
| W6 evidence | `backend/reports/w6_7_3_1_api_regression.md`, `w6_7_3_2_e2e_integration.md`, `w6_7_3_3_final_regression.md` |

## 6. Các điểm còn mở và rủi ro

1. **FR-12:** Lọc snapshot đã có; endpoint xuất báo cáo CSV chưa được xác nhận triển khai.
2. **FR-13:** `is_stale` kiểm tra snapshot hoàn tất đang được truy vấn; chưa có kết luận trực tiếp về freshness của latest completed snapshot theo camera.
3. **Job reliability:** FastAPI BackgroundTasks trong tiến trình, chưa có durable queue, tự phục hồi/retry theo cơ chế bền vững sau restart.
4. **Review history:** GET action đang suy luận `accept/correct` theo nhãn AI gốc; bảng `spot_reviews` chưa lưu `action` riêng để bảo toàn mọi ngữ nghĩa nghiệp vụ tương lai.
5. **Security & observability:** AI service cần chạy loopback/private; chưa xác nhận Backend CI chuyên biệt trên GitHub, giám sát cảnh báo và quy trình production.
6. **E2E coverage:** Chưa có kiểm thử xác nhận accuracy trên tập ảnh mới gắn ground truth, nhiều ô thật, thời tiết/ban đêm, tải lớn; cần phối hợp FE/AI để nghiệm thu demo đầy đủ.

## 7. Kết luận và điều kiện bàn giao

Ở phạm vi test W6 được ghi nhận, Backend đã vượt qua hồi quy API và luồng E2E **AI thật → Backend → PostgreSQL**, đồng thời có tài liệu as-built về yêu cầu, thiết kế, ERD và kiến trúc. Đây là minh chứng hoàn tất phạm vi Backend MVP được kiểm thử, **không** tự động đóng các yêu cầu chưa triển khai hoặc xác nhận sẵn sàng production.

Trước khi mở PR W6: kiểm tra file báo cáo không chứa mật khẩu, token, `.env` hoặc URL DB có credentials; đảm bảo các file bằng chứng được commit lên nhánh W6; chạy Git status và review diff. Chỉ chủ repo/nhóm trưởng quyết định merge.
