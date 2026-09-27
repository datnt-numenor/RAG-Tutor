# Giao diện RAGTutor

Đây là giao diện Next.js của RAGTutor. Tài liệu chính, kiến trúc và hướng dẫn chạy toàn bộ hệ thống nằm tại [`../README.md`](../README.md).

## Chạy trên máy cá nhân

Yêu cầu Node.js 22.

```powershell
Copy-Item .env.example .env.local
npm.cmd ci
npm.cmd run dev
```

- `http://localhost:3000/demo`: bản demo dùng dữ liệu mẫu, không gọi máy chủ.
- `http://localhost:3000`: ứng dụng đầy đủ, cần Supabase và FastAPI.

## Biến môi trường

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://<ma-du-an>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<khoa-cong-khai-hoac-an-danh>
```

Không đặt khóa `service_role` của Supabase, mật khẩu cơ sở dữ liệu hoặc khóa API của AI trong biến `NEXT_PUBLIC_*`.

## Kiểm tra trước khi đưa lên Git

```powershell
npm.cmd run lint
npm.cmd run build
```
