# AI Smart Parking

Đồ án giám sát bãi đỗ xe bằng ảnh từ **một camera cố định**. Người quản trị cấu hình polygon cho từng ô; AI phân loại vùng ảnh thành `empty` hoặc `occupied` và trả `unknown` khi điểm tin cậy dưới ngưỡng. Backend dự kiến quản lý snapshot, lịch sử, trạng thái FULL/STALE; frontend dự kiến hiển thị kết quả và cho chỉnh polygon.

## Trạng thái hiện tại

| Phần | Đã có trong repository | Việc còn lại |
|---|---|---|
| AI | Mã chuẩn bị dữ liệu, huấn luyện, đánh giá và FastAPI inference; đã kiểm thử riêng trên UFPR04 | Bàn giao checkpoint ngoài Git, thử trên máy đích và camera triển khai |
| Backend | SRS, use case, ERD và bản thiết kế API | Chưa có API chạy; cần hiện thực và tích hợp với AI |
| Frontend | Phạm vi giao diện trong tài liệu | Chưa có ứng dụng chạy; cần hiện thực dashboard và polygon editor |
| Toàn hệ thống | Hợp đồng và [kế hoạch nối backend ↔ AI](ai-service/docs/BACKEND_AI_INTEGRATION_PLAN.md) | Chưa có bằng chứng chạy end-to-end |

AI nhận ảnh và polygon đã cấu hình, tạo crop 224×224, chạy MobileNetV3-Small hai lớp, rồi áp ngưỡng softmax `0,90` cho `unknown`. AI **không** phát hiện ô đỗ, không tính FULL/STALE và không lưu database. Bộ test độc lập UFPR04 gồm 740 crop: accuracy trước ngưỡng **97,973%**, occupied-F1 **97,288%**; sau ngưỡng có 28 `unknown` và còn 2 trường hợp occupied bị nhận thành empty. Đây là kết quả trên tập dữ liệu đã thử, chưa chứng minh chất lượng ở camera khác. Xem [báo cáo W5](ai-service/reports/w5_evaluation_report.md).

## Phạm vi dự kiến

Một bãi thử nghiệm, một camera, snapshot JPEG/PNG, khoảng 100 ô. Admin cấu hình bãi/camera/polygon; Operator xem và xác minh; hệ thống dự kiến lưu lịch sử, thống kê và báo cáo. FULL chỉ khi có ít nhất một ô hợp lệ và mọi ô đều `occupied`; STALE do backend xác định từ thời điểm snapshot. Các chức năng nghiệp vụ này hiện vẫn là **thiết kế**, chưa phải tính năng đã chạy.

## Công nghệ và thành viên

| Thành phần | Công nghệ trong mã hoặc thiết kế | Phụ trách |
|---|---|---|
| AI | Python 3.11, PyTorch/torchvision, OpenCV, FastAPI, MobileNetV3-Small | Nguyễn Duy Khang |
| Backend | FastAPI, PostgreSQL (thiết kế) | Nguyễn Hoài Nam |
| Frontend | React, Vite (dự kiến) | Nguyễn Hoàng Minh Khôi |
| Triển khai | Docker Compose (kế hoạch) | Cả nhóm, Khôi phụ trách chính |

## Tìm nhanh trong repository

| Đường dẫn | Nội dung |
|---|---|
| [`ai-service/`](ai-service/README.md) | Hướng dẫn chạy AI; `src/` là inference, `scripts/` là dữ liệu/huấn luyện/đánh giá, `tests/` là kiểm thử |
| [`ai-service/docs/AI_API_CONTRACT.md`](ai-service/docs/AI_API_CONTRACT.md) | API AI thực tế `/health`, `/ready`, `/v1/infer` |
| [`ai-service/docs/BACKEND_AI_INTEGRATION_PLAN.md`](ai-service/docs/BACKEND_AI_INTEGRATION_PLAN.md) | Chỗ khác nhau giữa hợp đồng backend và API AI, cách chuyển đổi |
| [`ai-service/reports/`](ai-service/reports/final_ai_report.md) | Báo cáo dữ liệu, confidence, test độc lập và benchmark |
| [`backend/`](backend/README.md), [`frontend/`](frontend/README.md) | Phần việc chưa khởi tạo ứng dụng |
| [`docs/`](docs/WORKSPACE.md) | SRS, WBS, thiết kế backend và quy tắc cộng tác |

Xem [README AI](ai-service/README.md) để cài, kiểm thử và gọi service. Bản thiết kế nghiệp vụ ở [SRS](docs/requirements/SRS-draft.md) và [backend API contract](docs/api/backend-api-contract-v1.md); endpoint nội bộ `/predict` trong thiết kế backend **chưa khớp** `/v1/infer` của AI, nên cần Nam review adapter trước tích hợp.

Không commit ảnh dữ liệu lớn, checkpoint, token hoặc `.env` thật. Model release `v0.1.0-rc2` được bàn giao riêng, không nằm trong bản clone GitHub.
