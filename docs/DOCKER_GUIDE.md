# Chạy AI Smart Parking bằng Docker Compose

Tài liệu dành cho môi trường demo trên một máy. Compose tạo bốn dịch vụ: frontend, backend, AI chạy CPU và PostgreSQL. Các container dùng mạng nội bộ; chỉ frontend được mở trên máy tại `http://localhost:8080`.

## Chuẩn bị

- Docker Desktop với Linux containers, đã khởi động.
- Gói model `ai-smart-parking-model-v0.1.0-rc2` do nhóm AI bàn giao, đã giải nén và kiểm tra bằng `verify_release.py`.
- Thư mục model sau giải nén phải chứa `model/best.pt` và `threshold_candidate.json`. Model không nằm trong Git và không được đưa vào Docker image.
- Có kết nối Internet lần đầu để tải image và dependencies.

Compose tạo database và kho ảnh riêng trong Docker volumes. Dữ liệu PostgreSQL và ảnh khi chạy bằng Python trước đây không được tự động chuyển sang môi trường này.

## Cấu hình

Mở Command Prompt tại thư mục gốc repository:

```cmd
cd /d D:\UTH_K23\Do_an_thuc_te_CNPM\AI-Smart-Parking
copy compose.env.example compose.env
```

Mở `compose.env` bằng trình soạn thảo:

1. Đặt `PARKING_POSTGRES_PASSWORD` thành mật khẩu ngẫu nhiên chỉ gồm chữ và số. Ký tự đặc biệt trong mật khẩu cần được URL-encode trước khi đưa vào `DATABASE_URL`.
2. Đặt `PARKING_JWT_SECRET_KEY` thành chuỗi ngẫu nhiên ít nhất 32 byte. Có thể tạo chuỗi bằng `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Đặt `PARKING_MODEL_RELEASE_DIR` trỏ tới thư mục model đã giải nén. Dùng dấu `/` trong đường dẫn Windows; đường dẫn mẫu là đường dẫn tương đối so với thư mục repository.
4. Nếu cổng 8080 đã được sử dụng, đổi `PARKING_WEB_PORT`.

Không chia sẻ hoặc commit `compose.env`. Mật khẩu PostgreSQL chỉ được áp dụng khi tạo volume database lần đầu; sửa file sau đó không tự đổi mật khẩu database hiện có.

## Khởi động

```cmd
docker compose --env-file compose.env config --quiet
docker compose --env-file compose.env up --build -d
docker compose --env-file compose.env ps
```

Backend tự chạy migration trước khi khởi động. Kiểm tra log nếu dịch vụ backend dừng:

```cmd
docker compose --env-file compose.env logs backend
```

Kiểm tra AI đã nạp đúng model, không chỉ kiểm tra tiến trình còn sống:

```cmd
docker compose --env-file compose.env exec ai python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/ready').read().decode())"
```

Kết quả cần có `status: ready`, `model_version: mobilenetv3-small-w2-488ed38efe01` và `threshold: 0.9`. Nếu chưa sẵn sàng, xem `docker compose --env-file compose.env logs ai` và kiểm tra đường dẫn model.

## Tạo tài khoản

Ở lần đầu chạy, tạo tài khoản qua lệnh tương tác; không truyền mật khẩu trên dòng lệnh:

```cmd
docker compose --env-file compose.env exec backend python -m app.scripts.create_user --username admin01 --role admin
docker compose --env-file compose.env exec backend python -m app.scripts.create_user --username operator01 --role operator
```

Nhập mật khẩu theo lời nhắc. Sau đó mở `http://localhost:8080` và đăng nhập. Nếu đổi cổng, dùng cổng đã đặt trong `compose.env`.

## Dừng và chạy lại

```cmd
docker compose --env-file compose.env down
docker compose --env-file compose.env up -d
```

Lệnh `down` ở trên giữ lại database và ảnh trong volumes. Không thêm `-v` nếu cần giữ dữ liệu. Nếu thay cấu hình build của frontend hoặc Dockerfile, chạy lại `up --build -d`.

Thiết lập này cần được kiểm thử trên máy demo cụ thể. AI service không có xác thực riêng và chỉ dùng trong mạng Compose; không mở trực tiếp cổng AI ra bên ngoài.
