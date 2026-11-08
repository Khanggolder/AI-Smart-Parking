
# AI Smart Parking – Frontend

Frontend của đồ án AI Smart Parking, xây dựng bằng React và Vite.

Phụ trách: Nguyễn Hoàng Minh Khôi (Frontend / DevOps).

## 1. Công nghệ

- React
- Vite
- JavaScript
- CSS
- Lucide React
- Axios
- React Router DOM

## 2. Trạng thái hiện tại

Đã triển khai:
- React/Vite, đăng nhập, session và route theo quyền.
- Quản lý bãi xe, camera và Polygon Editor kết nối Backend.
- Dashboard tải snapshot, theo dõi job, hiển thị ảnh, polygon,
  kết quả dự đoán, KPI và trạng thái dữ liệu từ Backend W4.
- Wireframe, ESLint, Vite build và GitHub Actions CI.

Lịch sử hỗ trợ lọc snapshot theo camera, ngày và trạng thái xử lý;
báo cáo hiển thị chi tiết và xuất CSV cho từng snapshot hoàn thành.
Lịch sử hỗ trợ xác nhận hoặc sửa nhãn và xem các lần xác minh.
Dashboard cần Backend W4, database đã migration và AI Service đã nạp model;
cần kiểm thử toàn bộ luồng với môi trường và model thực tế.

## 3. Yêu cầu môi trường

- Node.js 22.12+ (khuyến nghị Node.js 22 LTS phù hợp).
- npm.
- Git.
- Trình duyệt Chrome, Edge hoặc tương đương.

## 4. Cài đặt và chạy

Clone repository:

    git clone https://github.com/Khanggolder/AI-Smart-Parking.git

Di chuyển vào dự án:

    cd AI-Smart-Parking

Chuyển sang nhánh Frontend trong giai đoạn phát triển:

    git switch feature/frontend-khoi

Di chuyển vào thư mục Frontend:

    cd frontend

Cài dependencies:

    npm ci

Khởi động môi trường phát triển:

    npm run dev

Mở trình duyệt tại:

http://localhost:5173

Lưu ý: Giữ Terminal chạy Vite trong lúc xem giao diện.
Nhấn Ctrl+C để dừng server.

Nếu cổng 5173 đang được sử dụng, Vite có thể chọn cổng khác.
Xem địa chỉ Local thực tế được hiển thị trong Terminal.

## 5. Kiểm tra chất lượng

Kiểm tra ESLint:

    npm run lint

Chạy kiểm thử frontend:

    npm test

Build phiên bản production:

    npm run build

Chạy thử phiên bản đã build:

    npm run preview

Các lệnh lint, test và build cũng được chạy trên
GitHub Actions thông qua workflow:

.github/workflows/frontend-ci.yml

## 6. Cấu hình môi trường

File mẫu:

    frontend/.env.example

Nội dung ví dụ:

    VITE_API_BASE_URL=http://localhost:8000/api/v1

Đây là địa chỉ Backend dự kiến theo API Contract v1.

Nếu cần thay đổi cấu hình local, có thể tạo file
frontend/.env.local với các giá trị phù hợp.

Không commit file môi trường chứa thông tin nhạy cảm.

Lưu ý: Biến bắt đầu bằng VITE_ có thể được đưa
vào ứng dụng trình duyệt, không dùng cho secrets.

## 7. Cấu trúc source

    frontend/
    ├── public/
    ├── src/
    │   ├── assets/
    │   ├── components/
    │   │   ├── Header.jsx
    │   │   ├── Sidebar.jsx
    │   │   └── StatCard.jsx
    │   ├── layouts/
    │   │   └── MainLayout.jsx
    │   ├── pages/
    │   │   ├── Cameras.jsx
    │   │   ├── Dashboard.jsx
    │   │   ├── History.jsx
    │   │   ├── ParkingLots.jsx
    │   │   ├── PolygonEditor.jsx
    │   │   └── Reports.jsx
    │   ├── App.jsx
    │   ├── App.css
    │   ├── main.jsx
    │   └── index.css
    ├── .env.example
    ├── package.json
    └── vite.config.js

Các file trang không đồng nghĩa các chức năng
đã được triển khai hoàn chỉnh.

## 8. Quy tắc hiển thị dữ liệu AI

Frontend lấy dữ liệu thông qua Backend.
Không gọi trực tiếp AI Service từ trình duyệt.

Quy ước màu ô đỗ:
- empty: xanh lá.
- occupied: đỏ.
- unknown: xám.

Hiển thị nhãn cuối do Backend cung cấp.
Không tự suy ra nhãn từ raw_label hoặc scores.

Hiển thị confidence, model_version và captured_at
khi Backend cung cấp.

Quy tắc FULL:
- total > 0
- empty == 0
- unknown == 0

STALE thể hiện dữ liệu snapshot đã cũ.
Không coi snapshot là video trực tiếp.

Khi AI/Backend lỗi, hiển thị thông báo phù hợp;
không tự chuyển trạng thái ô thành empty.

Dashboard sử dụng summary và trạng thái STALE do Backend cung cấp.
Ảnh snapshot được tải qua API có xác thực. Khi job mới thất bại,
kết quả thành công trước đó vẫn được hiển thị.

## 9. Tài liệu liên quan

- docs/wireframes/: thiết kế giao diện W1.
- docs/api/backend-api-contract-v1.md: hợp đồng API.
- ai-service/docs/FRONTEND_HANDOVER.md: quy ước hiển thị AI.
- CONTRIBUTING.md: quy trình làm việc Git.
- docs/planning/: kế hoạch công việc.

## 10. Lưu ý bảo mật

Không commit:
- Mật khẩu, token, API key.
- File .env chứa thông tin thật.
- Dataset hoặc checkpoint mô hình lớn.
- node_modules/ và dist/.

Chỉ coi kết quả là số liệu vận hành khi đã xác nhận đúng camera,
ảnh và cấu hình model trong môi trường triển khai.
