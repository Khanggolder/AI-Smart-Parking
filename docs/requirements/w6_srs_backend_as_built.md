# AI Smart Parking — W6 Backend SRS: đối chiếu yêu cầu và trạng thái triển khai

**Task:** 7.4.1 — Cập nhật SRS theo chức năng Backend thực tế.  
**Phạm vi:** Backend FastAPI + PostgreSQL + tích hợp AI; không khẳng định tính năng Frontend đã hoàn thành.  
**Nguồn đối chiếu:** `docs/requirements/SRS-draft.md`, `docs/requirements/backend-use-cases-test-matrix.md`, `backend/app/`, các báo cáo `backend/reports/w6_7_3_1_api_regression.md` và `backend/reports/w6_7_3_2_e2e_integration.md`.

> Đây là **phụ lục as-built** phục vụ cập nhật bản SRS chung, không thay thế hoặc tự ý chỉnh sửa bản SRS chính thức của nhóm.

## 1. Bối cảnh và phạm vi MVP

- Camera cố định có ảnh tham chiếu; Admin thiết lập polygon vùng ô đỗ, Operator theo dõi, upload ảnh và xác minh kết quả.
- AI phân loại ảnh từng vùng thành `empty`, `occupied` hoặc `unknown` (khi độ tin cậy dưới ngưỡng); **AI không phát hiện vị trí ô**, không quản lý dữ liệu trong PostgreSQL.
- Backend chịu trách nhiệm xác thực, cấu hình, lưu ảnh/snapshot/prediction, lịch sử, review, thống kê `FULL` và độ cũ `STALE` của snapshot.
- MVP kiểm chứng một camera; schema hỗ trợ nhiều bãi/camera. Không bao gồm thanh toán, biển số, đặt chỗ hoặc livestream RTSP.

## 2. Ma trận yêu cầu chức năng SRS → Backend hiện thực

| FR | Nội dung trong SRS | Backend W6 thực tế | Minh chứng / giới hạn |
|---|---|---|---|
| FR-01 | Đăng nhập, Admin/Operator | **Đã có** | `/auth/login`, `/auth/me`; JWT; kiểm tra role tại API; `backend/tests/test_auth.py` |
| FR-02 | Bãi xe, camera, ảnh tham chiếu | **Đã có Backend** | CRUD bãi/camera, PUT/GET ảnh tham chiếu; ảnh lưu file private |
| FR-03 | Thêm/sửa/vô hiệu hóa polygon | **Đã có Backend** | API spot; soft-deactivate; tăng camera `config_version`; UI là phần việc riêng |
| FR-04 | Kiểm tra hình học polygon | **Đã có Backend** | Tọa độ chuẩn hóa [0,1]; reject polygon sai/đụng/tự giao/quá nhỏ |
| FR-05 | Upload snapshot JPEG/PNG | **Đã có** | `POST /snapshots` → 202; kiểm tra MIME, nội dung, kích thước trùng ảnh tham chiếu |
| FR-06 | AI empty/occupied/unknown | **Đã tích hợp** | Backend gọi AI service `POST /v1/infer`, kiểm tra map spot/threshold; E2E thật W6 7.3.2 PASS |
| FR-07 | Hiển thị nhãn, confidence, polygon | **API đã hỗ trợ** | `GET /snapshots/{id}` trả prediction, confidence, polygon; việc hiển thị UI cần đánh giá FE riêng |
| FR-08 | Tổng ô và phân loại | **Đã có** | `total = empty + occupied + unknown` theo `effective_label` của snapshot hoàn thành |
| FR-09 | FULL khi tất cả occupied | **Đã có** | `FULL` chỉ khi có ô và tất cả `occupied`; `unknown` không tính là trống |
| FR-10 | Lưu snapshot và model version | **Đã có** | Snapshot lưu time/config/job_status; prediction giữ nhãn gốc, điểm và model version |
| FR-11 | Xác minh/sửa nhãn, giữ AI gốc | **Đã có** | POST/GET reviews, revision optimistic conflict, review append-only, audit |
| FR-12 | Lọc lịch sử, báo cáo, CSV | **Một phần** | `GET /snapshots` lọc theo camera/status/thời gian và phân trang; chưa thấy route CSV xuất báo cáo trong Backend W5/W6 |
| FR-13 | Cảnh báo STALE | **Một phần** | `GET /snapshots/{id}` trả `is_stale` cho *snapshot hoàn tất được hỏi*; chưa có API riêng tính freshness của snapshot hoàn tất mới nhất trên mỗi camera |
| FR-14 | Audit thao tác | **Đã có Backend** | `AuditLog` cho CRUD cấu hình, snapshot được nhận và review |
| FR-15 | Phát chuỗi ảnh timestamp | **Chưa xác nhận triển khai** | Ngoài các luồng snapshot hiện có |
| FR-16 | RTSP/video trực tiếp | **Chưa triển khai** | Ngoài phạm vi MVP |

## 3. Luồng nghiệp vụ được xác nhận

1. Admin tạo bãi/camera, upload ảnh tham chiếu, tạo polygon hợp lệ.
2. Admin hoặc Operator upload snapshot (multipart `camera_id`, `captured_at` timezone-aware, `image`). Backend kiểm tra dữ liệu, snapshot hóa `spots_at_capture` và trả **202** cùng UUID.
3. BackgroundTasks chuyển `queued` → `processing`, gọi AI rc2 `POST /v1/infer`; trên thành công lưu predictions và `completed` trong một DB transaction; lỗi ghi `failed/error_code`.
4. GET snapshot trả `predicted_label` (AI nguyên bản) và `effective_label` (review mới nhất nếu có), summary, `is_stale`.
5. Admin/Operator có thể `accept` hoặc `correct`, cần `expected_revision`, correction cần lý do; revision cũ trả **409**.
6. GET lịch sử review sắp theo revision tăng dần, có người review và thời điểm.

## 4. Tiêu chí nghiệm thu và bằng chứng W6

- **7.3.1 API regression:** người thực hiện báo `SUCCESS: W6 7.3.1 API regression test suite passed`; chi tiết trong `backend/reports/w6_7_3_1_api_regression.md`.
- **7.3.2 E2E với AI thật:** người thực hiện báo AI rc2 CPU READY; JWT login; POST snapshot 202; 1 prediction; PostgreSQL lưu snapshot/prediction/audit; GET ảnh và lịch sử đúng; chi tiết trong `backend/reports/w6_7_3_2_e2e_integration.md`.
- **Giới hạn bằng chứng:** kiểm thử E2E ở trên dùng ảnh tham chiếu 724×738, 1 polygon; **không** xác nhận độ chính xác trên ảnh mới hay tải 100 ô, không chứng minh hệ thống đã sẵn sàng production.
- **7.3.3:** người thực hiện cho biết đã chạy kiểm thử cuối; cần lưu đầu ra pytest/bug log riêng nếu sử dụng làm minh chứng nộp bài.

## 5. Yêu cầu còn mở trước khi nghiệm thu toàn hệ thống

- Hoàn thiện và test xuất CSV theo FR-12 nếu nhóm giữ yêu cầu này ở mức MUST.
- Định nghĩa và test cảnh báo latest-camera STALE theo FR-13; tránh coi riêng `is_stale` của một ảnh cũ là trạng thái hiện hành của camera.
- Đồng bộ và xác thực bản SRS Word chính thức, SDS và API Contract; bổ sung bằng chứng UI và demo cross-team.
- Test các tình huống thực tế: ảnh mới, nhiều polygon thật, unknown, AI offline, reset/restart Backend, upload lỗi.

## 6. Các giới hạn kỹ thuật đã biết

- Worker hiện dùng FastAPI `BackgroundTasks` trong tiến trình; không có durable queue, tự hồi phục job sau crash, retry/backoff bền vững.
- Review history hiện suy luận trường `action` từ `verified_label == predicted_label`; schema `spot_reviews` chưa có cột lưu `action` độc lập. Cần cân nhắc migration nếu nghiệp vụ đòi giữ lịch sử hành động chính xác trong mọi trường hợp.
- AI service là nội bộ, không tự xác thực; bind loopback/mạng riêng trong demo. Không commit `.env`, khóa JWT, password, ảnh thật hoặc checkpoint lên Git.
