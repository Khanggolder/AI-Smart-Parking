# AI Smart Parking

Đồ án giám sát bãi đỗ xe bằng ảnh từ camera cố định. Admin đặt polygon cho từng ô đỗ; AI phân loại vùng ảnh thành `empty` hoặc `occupied` và trả `unknown` khi điểm tin cậy dưới ngưỡng. Backend lưu snapshot, kết quả và lịch sử; frontend hỗ trợ cấu hình và xem kết quả.

## Phạm vi và cách hoạt động

Một bãi thử nghiệm có thể có nhiều camera, mỗi camera tối đa 100 ô đang hoạt động. Ảnh snapshot phải cùng góc nhìn và kích thước với ảnh tham chiếu của camera. Hệ thống xử lý ảnh chụp, không phát video trực tiếp hoặc tự phát hiện vị trí ô đỗ.

```text
React/Vite → FastAPI Backend → PostgreSQL
                    │
                    └── POST /v1/infer → FastAPI AI → MobileNetV3-Small
```

Frontend gửi ảnh và cấu hình qua Backend. Backend chuyển polygon `{x,y}` thành `[x,y]`, gọi AI, kiểm tra response rồi lưu toàn bộ dự đoán của một snapshot trong một giao dịch. `unknown` là kết quả AI chưa đủ tự tin; lỗi gọi AI được ghi là job `failed`. Backend tính `FULL` chỉ khi có ít nhất một ô và mọi ô đều `occupied`; `STALE` cho biết snapshot đã cũ.

## Chức năng hiện có

| Thành phần | Mã đã triển khai | Giới hạn kiểm chứng |
|---|---|---|
| AI | Chuẩn bị dữ liệu, huấn luyện, đánh giá, API inference và ngưỡng `unknown` | Test độc lập trên UFPR04; chưa xác nhận chất lượng ở camera khác |
| Backend | JWT và phân quyền, bãi xe/camera/polygon, ảnh tham chiếu, snapshot, adapter AI, lịch sử, xác minh dự đoán | Job chạy trong tiến trình web, chưa tự khôi phục sau restart |
| Frontend | Đăng nhập, cấu hình, Polygon Editor, Dashboard, lịch sử, review và xuất CSV từng snapshot | Lint, unit tests và build đã có; cần kiểm thử thao tác toàn luồng trên trình duyệt |
| Docker | Compose cho PostgreSQL, AI, Backend và Frontend | Cần thử với checkpoint thật trên máy demo cụ thể |

AI dùng Python 3.11, PyTorch, torchvision, OpenCV và FastAPI. Backend dùng FastAPI, SQLAlchemy, Alembic và PostgreSQL. Frontend dùng React/Vite. Nguyễn Duy Khang phụ trách AI và tích hợp chung; Nguyễn Hoài Nam phụ trách Backend và dữ liệu; Nguyễn Hoàng Minh Khôi phụ trách Frontend và Docker.

Kết quả test độc lập AI trên 740 crop UFPR04: accuracy hai lớp **97,973%**, occupied F1 **97,288%**. Với ngưỡng `0,90`, có **28 `unknown`** và **2 trường hợp có xe bị chấp nhận là trống**. Đây không phải độ chính xác toàn hệ thống trên camera triển khai. Xem [báo cáo đánh giá](ai-service/reports/w5_evaluation_report.md) và [Model Card](ai-service/docs/MODEL_CARD.md).

## Chạy demo

1. Lấy gói model `v0.1.0-rc2` qua kênh bàn giao của nhóm, giải nén và chạy `verify_release.py`. Checkpoint không nằm trên GitHub.
2. Cài Docker Desktop, sao chép `compose.env.example` thành `compose.env`, đặt mật khẩu PostgreSQL, JWT secret và `PARKING_MODEL_RELEASE_DIR` tới thư mục model đã giải nén.
3. Tại root repository, chạy:

   ```cmd
   docker compose --env-file compose.env config --quiet
   docker compose --env-file compose.env up --build -d
   docker compose --env-file compose.env ps
   ```

4. Kiểm tra AI `/ready`, tạo tài khoản Admin/Operator theo [hướng dẫn Docker](docs/DOCKER_GUIDE.md), rồi mở `http://localhost:8080`.
5. Tạo bãi và camera, tải ảnh tham chiếu, vẽ ô, tải snapshot cùng kích thước, chờ job hoàn tất, kiểm tra lịch sử và xuất CSV theo [hướng dẫn sử dụng](docs/USER_GUIDE.md).

Xem log bằng `docker compose --env-file compose.env logs backend ai frontend db`. Docker cần daemon đang chạy và gói model ở đúng đường dẫn trước khi khởi động.

## Tìm mã và tài liệu

| Đường dẫn | Nội dung |
|---|---|
| [ai-service/](ai-service/README.md) | `src/` xử lý ảnh và API, `scripts/` huấn luyện/đánh giá, `tests/` kiểm thử |
| [backend/](backend/README.md) | `app/api/` HTTP, `app/services/` AI adapter và job, `alembic/` migration |
| [frontend/](frontend/README.md) | `src/pages/` giao diện, `src/api/` kết nối Backend, `tests/` kiểm thử |
| [docs/](docs/WORKSPACE.md) | SRS, SDS, hợp đồng API, hướng dẫn Docker và sử dụng |

Backend từng chạy với AI thật và PostgreSQL cho **một ô** theo [báo cáo tích hợp](backend/reports/w6_7_3_2_e2e_integration.md). Trước buổi bảo vệ cần thử nhiều ô trên ảnh camera thật, toàn bộ thao tác trên trình duyệt và máy trình chiếu. Không commit `.env`, ảnh vận hành, dataset lớn hoặc checkpoint.
