# Git Workspace — AI Smart Parking

## Cấu trúc
```text
AI-Smart-Parking/
├── frontend/          # React + Vite (chưa khởi tạo code)
├── backend/           # FastAPI nghiệp vụ (chưa khởi tạo code)
├── ai-service/        # Python AI inference (chưa khởi tạo code)
├── docs/
│   ├── requirements/  # SRS
│   └── planning/      # WBS
├── tests/             # Tests khi phát triển
├── scripts/           # Công cụ xử lý dataset
├── README.md
├── CONTRIBUTING.md
├── .gitignore
└── .env.example
```

Git không theo dõi thư mục rỗng nên mỗi thư mục khởi tạo có file README mô tả trách nhiệm.

## Chuẩn bị buổi 18/10/2026
- [x] Tên đề tài, phạm vi MVP, deliverables dự kiến.
- [x] README, hướng dẫn Git, bản SRS/WBS tóm tắt để review.
- [ ] Đưa hai bản Word đã chỉnh sửa lên `docs/` (chưa tự động tải lên từ bản gốc).
- [ ] Xác nhận tài khoản GitHub của Nam và Khôi, mời làm collaborator.
- [ ] Tải dataset mẫu và kiểm tra polygon/annotation.
- [ ] Chốt ngày học, yêu cầu deploy, scope với giảng viên.

## Dữ liệu
Chọn ảnh từ một camera cố định; gắn đúng camera và phiên bản polygon. Dataset chỉ phục vụ huấn luyện/đánh giá; ảnh demo chạy inference độc lập.

## Sản phẩm bàn giao dự kiến
SRS/SDS, WBS, web app, backend API, AI model + metric report, schema/ERD, test report, Docker/README, slides và demo.

## Mục tiêu buổi review
Chứng minh bài toán có phạm vi thực hiện được với 3 người trong 6 tuần **dự kiến**; chưa cần hệ thống hoàn thiện.
