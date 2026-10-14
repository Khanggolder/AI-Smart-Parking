# WBS sơ bộ v0.1 — kế hoạch nhóm 3 người

**W0:** chuẩn bị trước review 18/10/2026. **W1–W6:** lịch 6 tuần dự kiến sau khi được giảng viên góp ý.

## Phân công
| Thành viên | Vai trò | Trách nhiệm |
|---|---|---|
| Nguyễn Duy Khang | AI/Data, nhóm trưởng | Dataset, splits, baseline, model, AI service, metrics |
| Nguyễn Hoài Nam | Backend/BA | SRS, Use Case, ERD/API, database, auth, CRUD, kết nối AI |
| Nguyễn Hoàng Minh Khôi | Frontend/DevOps | UI/UX, polygon editor, dashboard, Docker, CI, demo |

## Mốc
| Mốc | Deliverable |
|---|---|
| W0 | Scope, SRS/WBS, repo, khảo sát dataset mẫu |
| W1 | SRS cập nhật, thiết kế UI, ERD/API, dataset split |
| W2 | Khung backend/frontend, auth/CRUD, baseline AI |
| W3 | Polygon editor, inference API, mô hình ứng viên |
| W4 | Ảnh → inference → hiển thị ô đỗ & sức chứa |
| W5 | Lịch sử, xác minh, báo cáo, test AI |
| W6 | Docker/CI, regression test, báo cáo, demo |

## Gói công việc ưu tiên để tạo Issue
- **W0 / AI:** tải mẫu PKLot/MetaPKLot, kiểm tra ảnh, polygon, nhãn và giấy phép.
- **W0 / Backend–BA:** đồng bộ SRS FR/NFR, Use Case, sơ đồ dữ liệu sơ bộ.
- **W0 / Frontend–DevOps:** wireframe, cấu trúc repo, workflow cộng tác.
- **W1 / AI:** dataset manifest và chia tập không rò rỉ.
- **W1 / Backend:** ERD và API contract.
- **W1 / Frontend:** wireframe quản lý bãi/ô đỗ và polygon editor.

## Definition of Done
Sản phẩm chạy được theo README, test các luồng chính, tài liệu khớp sản phẩm, số đo AI từ inference thật, không lưu secret/dataset lớn vào repo.

**Ghi chú:** Bản WBS Word trước đó có giờ công theo thành viên không khớp danh sách việc. Cần điều chỉnh số giờ và người phụ trách trong Word trước khi nộp. Đây là bản tóm tắt, không thay thế bảng WBS chi tiết.
