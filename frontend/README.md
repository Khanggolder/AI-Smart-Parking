# Frontend — AI Smart Parking

Ứng dụng React/Vite cho Admin và Operator. Admin cấu hình bãi xe, camera, ảnh tham chiếu và polygon. Cả hai vai trò có thể tải snapshot, xem Dashboard/lịch sử, xác minh dự đoán và xuất CSV của một snapshot hoàn thành. Frontend gọi Backend qua HTTP; trình duyệt không gọi AI trực tiếp.

## Chạy local

Cần Node.js 22.12+ và npm. Từ root repository:

```powershell
cd frontend
npm ci
npm run dev
```

Mở địa chỉ Vite in trên terminal, thường là `http://localhost:5173`. Mặc định frontend gọi `http://localhost:8000/api/v1`; nếu Backend ở địa chỉ khác, tạo `frontend/.env.local` theo [`.env.example`](.env.example) và đặt `VITE_API_BASE_URL`. Biến `VITE_` xuất hiện trong bundle trình duyệt, không đặt secret vào đây. Backend local cho phép origin `localhost:5173` và `127.0.0.1:5173` mặc định; nếu Vite chọn cổng khác, cập nhật `CORS_ORIGINS` của Backend.

Chạy bằng Docker Compose từ root theo [hướng dẫn Docker](../docs/DOCKER_GUIDE.md). Bản build Docker dùng `/api/v1` qua Nginx proxy tới Backend và mở giao diện ở `http://localhost:8080`.

## Chức năng và giới hạn

- Đăng nhập JWT, giữ token trong `sessionStorage`, kiểm vai trò qua `/auth/me`, đăng xuất.
- Quản lý bãi xe/camera, tải ảnh tham chiếu, vẽ và lưu polygon theo phiên bản camera.
- Dashboard tải snapshot và polling job; hiển thị ảnh, polygon, nhãn, confidence, thống kê `FULL`/`AVAILABLE`/`UNDETERMINED` và `STALE` từ Backend.
- Lịch sử có lọc, phân trang, review nhãn và xem các lần xác minh. Trang Báo cáo xuất CSV cho snapshot đã chọn ở trình duyệt.

`empty` hiển thị xanh, `occupied` đỏ, `unknown` xám. Frontend dùng `effective_label` do Backend cung cấp; không tự suy nhãn từ scores. Nếu job lỗi, giao diện không coi ô đó là trống. Ảnh snapshot là ảnh chụp theo thời điểm, không phải video trực tiếp.

Các trang `/dev/*` trong Vite development dùng dữ liệu mẫu để xem trạng thái UI; route thực sau đăng nhập dùng Backend. Lint, test và build chưa thay cho kiểm thử thao tác đầy đủ trên trình duyệt với AI và PostgreSQL thật.

## Kiểm thử

```powershell
npm run lint
npm test
npm run build
```

Workflow [frontend CI](../.github/workflows/frontend-ci.yml) chạy các lệnh tương ứng. Xem [hướng dẫn sử dụng](../docs/USER_GUIDE.md) cho các bước thao tác và [backend README](../backend/README.md) cho API, migration, tài khoản.
