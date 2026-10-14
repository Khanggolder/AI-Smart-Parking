# AI Smart Parking

**Xây dựng hệ thống giám sát và quản lý bãi đỗ xe thông minh ứng dụng Computer Vision và AI**

> Đồ án thực tế Công nghệ phần mềm • Trường Đại học Giao thông vận tải TP. HCM (UTH)  
> **Giai đoạn:** Chuẩn bị review scope, SRS, WBS và Git Workspace (18/10/2026).  
> **Trạng thái:** Dự án đang khởi động — chưa có mô hình hoặc ứng dụng hoàn chỉnh.

## Bài toán

Từ ảnh chụp của **một camera cố định**, quản trị viên định nghĩa các vị trí đỗ bằng polygon. Hệ thống dùng mô hình phân loại ảnh ô đỗ để dự đoán `empty` / `occupied`; trả `unknown` nếu không đủ tin cậy. Giao diện hiển thị các vùng có màu, tổng số ô, ô trống/đã chiếm/chưa xác định, cảnh báo đầy bãi, lịch sử và xác minh của nhân viên.

**Lưu ý:** Nhãn gốc dataset (*ground truth*) chỉ dùng để huấn luyện/đánh giá. Demo phải chạy suy luận thật trên ảnh đầu vào, không đọc nhãn sẵn để giả lập kết quả AI.

## Phạm vi MVP (dự kiến chốt với giảng viên)

- Đăng nhập/phân quyền `Admin` và `Operator`.
- 01 bãi xe thử nghiệm, 01 camera cố định; ảnh tham chiếu để tạo/sửa/xóa polygon ô đỗ.
- Upload ảnh JPEG/PNG; suy luận cho từng ô; các trạng thái `empty`, `occupied`, `unknown`.
- Thống kê sức chứa, FULL khi **có ít nhất 1 ô hợp lệ** và tất cả ô đều occupied; STALE khi dữ liệu quá thời hạn cấu hình.
- Lưu snapshot, model version, dự đoán, lịch sử, thao tác xác minh; lọc và xuất báo cáo CSV.

**Ngoài phạm vi:** thu phí, đặt chỗ, nhận diện biển số, cổng ra/vào, streaming camera 24/7, đa camera quy mô lớn, ước lượng thời gian đỗ chính xác đến giây.

## Công nghệ dự kiến

| Thành phần | Công nghệ |
|---|---|
| Frontend | React + Vite |
| Backend nghiệp vụ | FastAPI (Python) |
| Cơ sở dữ liệu | PostgreSQL |
| AI | PyTorch, MobileNetV3-Small/ResNet18 (baseline) |
| Triển khai thử nghiệm | Docker Compose |
| Quản lý | GitHub Issues, feature branches, Pull Requests |

Đây là công nghệ **đề xuất**, có thể thay đổi sau khi kiểm tra dữ liệu mẫu.

## Thành viên

| Thành viên | Vai trò | Phần việc chính |
|---|---|---|
| Nguyễn Duy Khang | Nhóm trưởng / AI–Data | Dataset, annotation, splits, mô hình, inference, đánh giá |
| Nguyễn Hoài Nam | Backend / BA | SRS, Use Case, ERD/API, auth, CRUD, tích hợp |
| Nguyễn Hoàng Minh Khôi | Frontend / DevOps | UI/UX, polygon editor, dashboard, Docker, demo |

Cả nhóm tham gia review chéo, kiểm thử và vấn đáp.

## Tài liệu & workspace

- [SRS sơ bộ (bản tóm tắt)](docs/requirements/SRS-draft.md)
- [WBS sơ bộ (bản tóm tắt)](docs/planning/WBS-draft.md)
- [Hướng dẫn cộng tác Git](CONTRIBUTING.md)
- [Cấu trúc workspace](docs/WORKSPACE.md)

**Ngày 18/10/2026:** review tên đề tài, phạm vi, deliverables, SRS/WBS và Git Workspace. **W1–W6** chỉ là kế hoạch dự kiến, chưa phải lịch học chính thức.

## Nguồn dữ liệu dự kiến

- [PKLot](https://web.inf.ufpr.br/vri/databases/parking-lot-database/)
- [MetaPKLot](https://github.com/DSBD-Research/MetaPKLot-Dataset)

Chưa kết luận chất lượng hoặc quyền phân phối lại dữ liệu trước khi tải và kiểm tra điều khoản. **Không commit** dataset lớn, model weights, mật khẩu, token hoặc file `.env` thật.

---
*Tài liệu khởi tạo workspace: 15/10/2026.*
