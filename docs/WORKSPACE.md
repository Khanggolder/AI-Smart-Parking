# Tài liệu AI Smart Parking

| Nơi bắt đầu | Nội dung |
|---|---|
| [README gốc](../README.md) | Phạm vi, trạng thái và cách chạy demo |
| [Hướng dẫn Docker](DOCKER_GUIDE.md) | Cấu hình và khởi động bốn dịch vụ |
| [Hướng dẫn sử dụng](USER_GUIDE.md) | Các bước thao tác Admin/Operator |
| [SRS as-built](requirements/w6_srs_backend_as_built.md) | Yêu cầu nghiệp vụ và trạng thái hiện thực |
| [SDS as-built](design/w6_sds_backend_as_built.md) | Kiến trúc Backend hiện tại |
| [Backend API contract](api/backend-api-contract-v1.md) | Endpoint và payload |
| [AI README](../ai-service/README.md) | Model, đánh giá và API AI |

`frontend/` chứa React/Vite, `backend/` chứa FastAPI và migration, `ai-service/` chứa source inference, script huấn luyện/đánh giá và báo cáo. Các file W1 trong `docs/` ghi lại thiết kế ban đầu; khi cần trạng thái hiện thực, ưu tiên source và tài liệu W6 as-built. Dataset ảnh và checkpoint không lưu trên GitHub.
