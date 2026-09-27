# Máy chủ RAGTutor

Đây là dịch vụ FastAPI của RAGTutor, chịu trách nhiệm xác thực, quản lý dự án và tài liệu, truy xuất RAG, bài kiểm tra, OCR, lộ trình học, tiến độ và các tác vụ chạy nền bằng Celery.

Tài liệu tổng quan và hướng dẫn chạy toàn bộ hệ thống nằm tại [`../README.md`](../README.md).

## Công nghệ chính

- Python 3.12, FastAPI và Pydantic.
- Supabase Auth, PostgreSQL, pgvector và kho lưu trữ tệp.
- Redis và Celery cho xử lý nền.
- Sentence Transformers cho vector biểu diễn 384 chiều.
- Groq và Gemini cho sinh nội dung; Azure Vision hỗ trợ OCR tùy chọn.

## Chuẩn bị môi trường

Chạy từ thư mục `backend`:

```powershell
py -3.12 -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install --upgrade pip
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền các giá trị cần thiết trong `.env`. Không đưa tệp này, mật khẩu cơ sở dữ liệu, khóa `service_role` của Supabase hoặc khóa API lên Git.

Các nhóm biến chính:

- Supabase và PostgreSQL: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`, `DIRECT_URL`.
- AI: `GEMINI_API_KEY`; `GROQ_API_KEY` và Azure Vision là tùy chọn.
- Ứng dụng: `APP_ENV`, `SECRET_KEY`, `ALLOWED_ORIGINS`.
- Tác vụ nền: `REDIS_URL`.
- Vector biểu diễn: `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_BATCH_SIZE`.

Danh sách đầy đủ và giá trị mẫu nằm trong [`.env.example`](.env.example).

## Chuẩn bị cơ sở dữ liệu

Áp dụng các tệp SQL trong `migrations/` theo thứ tự tên vào dự án Supabase. Các migration này tạo lược đồ dữ liệu, hàm tìm kiếm vector, chỉ mục, trigger và chính sách RLS.

Mọi bảng công khai phải bật RLS. Khóa `SUPABASE_SERVICE_KEY` chỉ được sử dụng ở máy chủ và không được đưa vào biến `NEXT_PUBLIC_*`.

## Khởi động dịch vụ

Khởi động Redis từ thư mục gốc của kho mã nguồn:

```powershell
docker compose up -d redis
```

Khởi động API từ thư mục `backend`:

```powershell
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Khởi động tiến trình Celery trong một cửa sổ lệnh khác:

```powershell
..\.venv\Scripts\python.exe -m celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo
```

Các địa chỉ phát triển:

- Tài liệu API: `http://127.0.0.1:8000/docs`
- Kiểm tra trạng thái: `http://127.0.0.1:8000/health`
- Kiểm tra Supabase và Redis: `http://127.0.0.1:8000/health/ready`

## Kiểm thử

Chạy toàn bộ kiểm thử máy chủ từ thư mục `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q --basetemp=.pytest-tmp -p no:cacheprovider
```

Các tập lệnh trong `scripts/` dùng để kiểm thử đầu-cuối:

- `smoke_e2e.py`: kiểm tra đăng nhập, tải tài liệu, nhập liệu và hỏi đáp có trích dẫn.
- `security_e2e.py`: kiểm tra cô lập dữ liệu và phân quyền giữa hai người dùng.
- `full_e2e.py`: kiểm tra luồng chức năng mở rộng.
- `manage_e2e_users.py`: tạo và xóa tài khoản kiểm thử tạm thời.

Các bài kiểm thử đầu-cuối cần API, Redis, Celery, Supabase và khóa AI hoạt động. Chỉ sử dụng tài khoản và dữ liệu kiểm thử riêng.

## Prisma

`prisma/schema.prisma` được giữ để mô tả mô hình quan hệ và hỗ trợ một số công cụ tùy chọn. Phần lớn luồng đang chạy sử dụng Supabase trực tiếp, vì vậy không bắt buộc sinh Prisma Client để khởi động API thông thường.

Khi cần dùng lớp truy cập dữ liệu dựa trên Prisma:

```powershell
..\.venv\Scripts\python.exe -m prisma generate --schema=prisma/schema.prisma
```

Hai cột vector `embedding` và `question_embedding` không nằm trong Prisma schema. Chúng được quản lý bằng SQL migration và truy vấn qua hàm Supabase như `match_chunks`.

Không dùng `prisma db push` trên môi trường vận hành; hãy sử dụng các migration SQL đã được quản lý phiên bản.

## Cấu trúc thư mục

```text
backend/
├── app/
│   ├── api/v1/endpoints/  # Các điểm cuối FastAPI
│   ├── core/              # Cấu hình, xác thực, cơ sở dữ liệu
│   ├── models/            # Mô hình dữ liệu
│   ├── repositories/      # Lớp truy cập dữ liệu tùy chọn
│   ├── schemas/           # Kiểu dữ liệu vào và ra
│   ├── services/          # Nghiệp vụ RAG, bài kiểm tra, OCR, lộ trình
│   └── workers/           # Các tác vụ Celery
├── evaluation/            # Công cụ đánh giá RAG
├── migrations/            # Migration SQL, pgvector và RLS
├── prisma/                # Mô hình quan hệ Prisma
├── scripts/               # Tập lệnh quản trị và kiểm thử đầu-cuối
├── tests/                 # Kiểm thử tự động
├── Dockerfile
├── main.py
└── requirements.txt
```

## Triển khai

`Dockerfile` tạo ảnh Python 3.12 không đặc quyền, cài PyTorch bản CPU và tải trước mô hình embedding để giảm thời gian khởi động. Khi triển khai cần cấu hình riêng API, tiến trình Celery và Redis, đồng thời đặt toàn bộ thông tin bí mật trong kho bí mật của nhà cung cấp.
