# AI Smart Parking — Backend Use Cases & Traceability (W1 / 2.1)

**Trạng thái:** Quy ước triển khai v1, chốt nội bộ theo SRS sơ bộ (15/10/2026) và Issue #2/#4.  
**Phụ trách:** Backend/BA (Nguyễn Hoài Nam).  
**Phạm vi:** MVP 01 bãi, 01 camera cố định, snapshot JPEG/PNG; không có live RTSP/thu phí/đặt chỗ/biển số.  
**Mục tiêu:** Cung cấp hồ sơ yêu cầu, luồng xử lý, ngoại lệ, ca kiểm thử để truy vết mã nguồn Backend khi thực hiện W2–W6.

## 1. Actor, quyền và dữ liệu nguồn

- **Admin:** quản lý cấu hình bãi xe/camera/ô đỗ và ảnh tham chiếu; xem dashboard, snapshot, báo cáo; được upload và xác minh.
- **Operator:** xem thông tin bãi xe/camera/ô đỗ, upload snapshot, xem kết quả/lịch sử, chấp nhận hoặc hiệu chỉnh dự đoán; **không** chỉnh cấu hình bãi/camera/ô đỗ.
- **AI service:** nhận ảnh snapshot và tập polygon **cùng camera**; dự đoán `empty`/`occupied`/`unknown` + `confidence`, `model_version` — không lấy ground truth làm prediction.
- Không có endpoint CRUD User công khai trong MVP; tạo tài khoản khởi đầu bằng script/seed nội bộ, mật khẩu băm.

## 2. Các quy tắc nghiệp vụ quyết định (Business Rules)

| ID | Quy tắc cố định cho bản v1 | Liên kết yêu cầu |
|---|---|---|
| BR-01 | `total = empty + occupied + unknown` của tập ô hợp lệ thuộc **cấu hình tại lúc chụp ảnh** | FR-08, NFR-03 |
| BR-02 | `FULL = total > 0 && empty == 0 && unknown == 0`; tổng bằng 0 không được là FULL | FR-09 (làm rõ Issue #2) |
| BR-03 | Nếu `unknown > 0` và `empty == 0`, hiển thị `UNDETERMINED`, không hiển thị FULL | FR-09 |
| BR-04 | `occupancy_rate = occupied / total * 100`; với `total == 0`, trả `null`, không chia 0 | FR-08 |
| BR-05 | Polygon phải có ≥3 điểm phân biệt, thuộc [0,1], không tự giao, diện tích > 0; mã ô duy nhất trong camera | FR-03/04 |
| BR-06 | Nhân viên sửa nhãn bằng `SpotReview`, tuyệt đối không sửa `SpotPrediction.predicted_label` | FR-11 |
| BR-07 | Trả `STALE` nếu snapshot thành công gần nhất đã cũ hơn `STALE_THRESHOLD_MINUTES` (mặc định 30 trong `.env.example`); không giả dữ liệu là live | FR-13 |
| BR-08 | Lỗi xử lý ảnh/AI không làm mất các snapshot thành công trước; snapshot thất bại giữ `job_status=failed` và mã lỗi | UC-02/NFR-04 |
| BR-09 | Polygon thay đổi tăng `camera.config_version`. Snapshot lưu phiên bản và polygon tại lúc suy luận để lịch sử không bị sai vùng | FR-10/11 |
| BR-10 | Mọi thời gian lưu UTC có timezone; hiển thị giờ Việt Nam tại UI (nếu cần) | FR-10, NFR-03 |
| BR-11 | Quyền được kiểm tra tại API, không dựa vào ẩn nút trên frontend | FR-01/NFR-05 |

## 3. UC-01 — Admin cấu hình ô đỗ

**Actor:** Admin. **Tiền điều kiện:** Đăng nhập hợp lệ, camera đã có ảnh tham chiếu và kích thước ảnh.

**Luồng chính:**
1. Admin chọn camera → Frontend GET danh sách vùng hiện tại.
2. Admin vẽ/sửa đa giác, đặt mã `P01...` trên ảnh tham chiếu.
3. Frontend chuyển sang tọa độ chuẩn hóa `(x,y)` trong `[0,1]` rồi gọi POST/PATCH API.
4. Backend xác minh token, role, camera, mã trùng, số điểm, diện tích, biên và tự giao.
5. Backend ghi thay đổi thành giao dịch DB, tăng `config_version`, ghi AuditLog, trả ID và polygon đã lưu.
6. Frontend GET lại danh sách để đối chiếu ID, tọa độ và vị trí.

**Ngoại lệ:** 401 chưa xác thực; 403 Operator chỉnh sửa; 404 camera/spot không tồn tại; 409 mã ô trùng; 422 polygon sai; 409 bản cấu hình đồng thời đã thay đổi. Không thay đổi dữ liệu đã lưu khi kiểm tra thất bại.

**Hậu điều kiện:** Ảnh tham chiếu và các ô khớp phiên bản cấu hình mới.

## 4. UC-02 — Upload snapshot, dự đoán và giám sát

**Actor:** Admin hoặc Operator. **Tiền điều kiện:** Đăng nhập; camera đã có vùng đỗ hợp lệ.

**Luồng chính:**
1. Người dùng upload ảnh JPEG/PNG + `camera_id` + `captured_at`.
2. Backend kiểm tra MIME, chữ ký dữ liệu ảnh, kích thước bytes, khả năng giải mã ảnh và quyền.
3. Backend tạo Snapshot với `job_status=queued`, ghi `config_version` và ảnh an toàn.
4. Backend xử lý job, gửi ảnh và polygon tương ứng cho AI service; job chuyển `processing`.
5. Nhận kết quả có spot ID hợp lệ, nhãn, confidence, model version; lưu dự đoán cho từng spot (hoặc xử lý đầy đủ trường hợp lỗi theo contract).
6. Tính `total/empty/occupied/unknown/occupancy_rate/full` từ prediction; lưu Snapshot `completed`.
7. Frontend polling GET snapshot theo ID, rồi hiện polygon trạng thái và cảnh báo.

**Ngoại lệ:** ảnh thiếu/hỏng/sai định dạng/quá giới hạn; camera chưa có polygon; timeout hay AI unavailable; AI trả sai spot IDs/trùng ID/thiếu model_version; job thất bại không làm mất snapshot đã thành công. Không hiển thị FULL nếu có unknown.

**Hậu điều kiện:** Có snapshot và dấu vết job; snapshot hoàn thành có dự đoán cho tất cả spot snapshot hóa.

## 5. UC-03 — Xác minh và xuất báo cáo

**Actor:** Admin/Operator. **Tiền điều kiện:** Có snapshot và prediction đã hoàn tất.

**Luồng chính:**
1. Người dùng lọc lịch sử theo ngày, camera và trạng thái.
2. Mở snapshot, xem prediction gốc, polygon trên ảnh, confidence.
3. Chấp nhận hoặc sửa một dự đoán bằng POST review, cung cấp `expected_revision`.
4. Backend xác minh quyền/phiên bản; tạo SpotReview append-only, ghi reviewer/changed_at và audit.
5. GET snapshot trả `predicted_label` cùng `effective_label` (review mới nhất hoặc prediction gốc), không ghi đè nhãn gốc.
6. Xuất CSV từ bộ lọc hiện tại.

**Ngoại lệ:** nhãn không hợp lệ; 401/403; 404 prediction; 409 chỉnh sửa đồng thời; 422 dữ liệu không hợp lệ.

## 6. Ma trận FR → API → Test

| FR / NFR | API / Thành phần | Bằng chứng kiểm thử |
|---|---|---|
| FR-01, NFR-05 | `/auth/login`, `/auth/me`, RBAC middleware/dependency | T-01 token sai → 401; T-02 Operator POST spot → 403 |
| FR-02 | `/parking-lots`, `/cameras` | T-03 Admin CRUD; T-04 tài nguyên không tồn tại → 404 |
| FR-03/04 | `/cameras/{id}/spots`, `/spots/{id}` | T-05 lưu/GET lại ≥10 vùng; T-06 trùng mã → 409; T-07 đa giác tự giao → 422 |
| FR-05 | `POST /snapshots` | T-08 JPEG/PNG hợp lệ; T-09 MIME giả/hỏng → 415/422; T-10 quá bytes → 413 |
| FR-06/07, NFR-04 | inference adapter, GET snapshot | T-11 AI trả nhãn/confidence/model_version; T-12 AI offline → failed nhưng vẫn xem lịch sử cũ |
| FR-08/09, NFR-03 | thống kê snapshot | T-13 còn ô trống; T-14 toàn occupied; T-15 unknown>0; T-16 total=0 không FULL |
| FR-10/11 | `/snapshots/{id}`, `/predictions/{id}/reviews` | T-17 nhãn gốc bất biến; T-18 sửa lưu reviewer; T-19 conflict → 409 |
| FR-12 | `/snapshots`, `/reports/snapshots.csv` | T-20 lọc ngày/camera/trạng thái; T-21 CSV xuất đúng bộ lọc |
| FR-13 | latest snapshot/STALE | T-22 ảnh quá ngưỡng; T-23 ảnh gần đây không STALE |
| FR-14 (SRS Word: SHOULD) | AuditLog, ghi review bắt buộc cho UC-03 | T-24 reviewer và lịch sử thao tác, không chứa mật khẩu/token |
| NFR-01/02/07 | báo cáo metric từ AI, integration benchmark | T-25 đo F1, p50/p95 với phần cứng và tập test rõ ràng |

**Liên kết nghiệm thu SRS:** AT-01 → T-05–07; AT-02 → T-08–12; AT-03 → T-13–16; AT-04 → T-17–19; AT-05 → T-20–23; AT-06 → T-01–02; AT-07 → T-25.

## 7. Những điều nằm ngoài phạm vi MVP

- Không nhận diện biển số, thanh toán, đặt chỗ, kiểm soát cổng, RTSP live liên tục hay multi-camera quy mô lớn.
- Không khẳng định F1/độ trễ đạt mục tiêu cho tới khi nhóm AI đo thật.
- API và schema mô tả trong bộ hồ sơ là **hợp đồng thiết kế**, chưa phải các endpoint đã chạy.
