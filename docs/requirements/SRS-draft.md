# SRS sơ bộ v0.1 — tóm tắt

**Đề tài:** Xây dựng hệ thống giám sát và quản lý bãi đỗ xe thông minh ứng dụng Computer Vision và AI.  
**Giảng viên:** Vũ Đình Long. **Nhóm:** Nguyễn Duy Khang, Nguyễn Hoài Nam, Nguyễn Hoàng Minh Khôi.  
**Mục đích:** Review phạm vi và yêu cầu ngày 18/10/2026. **Bản Word chính thức của nhóm cần bổ sung riêng.**

## Bài toán
Một camera cố định chụp bãi đỗ; Admin tạo polygon vị trí đỗ; AI suy luận trạng thái `empty/occupied`, hệ thống đặt `unknown` nếu độ tin cậy thấp/không xử lý được; Operator xác minh trạng thái. Không phải phần mềm thu phí hoặc xử phạt.

## MVP
Một bãi xe, một camera cố định; khoảng 100 ô; ảnh snapshot JPEG/PNG; quản lý dữ liệu, dashboard, cảnh báo, lịch sử và báo cáo.

## Functional requirements
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-01 | Đăng nhập và phân quyền Admin/Operator | MUST |
| FR-02 | Quản lý bãi xe/camera/ảnh tham chiếu | MUST |
| FR-03 | Vẽ, sửa, xóa và tải lại polygon | MUST |
| FR-04 | Kiểm tra hình học polygon | MUST |
| FR-05 | Tải snapshot hợp lệ | MUST |
| FR-06 | Suy luận empty/occupied và xử lý unknown | MUST |
| FR-07 | Hiển thị nhãn, confidence, polygon | MUST |
| FR-08 | Tính empty + occupied + unknown bằng tổng ô hợp lệ | MUST |
| FR-09 | FULL khi tổng ô > 0 và tất cả occupied, không unknown | MUST |
| FR-10 | Lưu ảnh, thời gian, model version, trạng thái từng ô | MUST |
| FR-11 | Xác minh/sửa nhãn, giữ nguyên dự đoán gốc | MUST |
| FR-12 | Lọc lịch sử, báo cáo và xuất CSV | MUST |
| FR-13 | Cảnh báo STALE khi không cập nhật snapshot theo ngưỡng | MUST |
| FR-14 | Nhật ký thao tác cấu hình/xác minh | MUST (đề xuất sửa v0.1) |
| FR-15 | Phát chuỗi ảnh có timestamp | SHOULD |
| FR-16 | Kết nối video/RTSP | COULD |

## Non-functional requirements (mục tiêu dự kiến)
- F1 cho `occupied` ≥ 0,90 trên test tách theo ngày; đo Precision/Recall/confusion matrix.
- Ảnh 1280×720, ≤100 ô: mục tiêu xử lý ≤15 giây trên thiết bị demo; đo p50/p95.
- Mật khẩu băm, kiểm tra quyền phía backend, xác thực upload.
- Có hướng dẫn chạy, Docker, version model và bộ kiểm thử.
- Trạng thái `unknown` không bị tính là ô trống; ảnh cũ có cảnh báo STALE.

## Data & kiến trúc
- Dataset ứng viên: PKLot/MetaPKLot; xác minh quyền và tính khớp annotation trước triển khai.
- Tách tập train/validation/test theo ngày hoặc camera để tránh rò rỉ.
- Frontend React/Vite ↔ backend FastAPI ↔ PostgreSQL; backend gọi AI module PyTorch.
- Các thực thể: User, ParkingLot, Camera, ParkingSpot, Snapshot, SpotPrediction, SpotReview, AuditLog.

## Tiêu chí chấp nhận ban đầu
- Lưu/tải lại polygon đúng tọa độ.
- Ảnh test không kèm ground truth đi qua inference và hiện nhãn/confidence.
- Kiểm tra 3 tình huống: còn chỗ, hết chỗ, có unknown.
- Lưu được lịch sử, xác minh và xuất CSV; quyền Admin/Operator đúng.

## Chưa chốt
Lịch chính thức; deploy local hay online; ngưỡng STALE; phần cứng benchmark; lựa chọn subset dữ liệu và thông số AI cuối cùng.

**Ghi chú:** Bản Markdown này là bản tóm tắt có đề xuất sửa FR-09/FR-14/UNKNOWN/STALE so với Word nhóm gửi trước đó. Hai bản phải được đồng bộ trước khi nộp.
