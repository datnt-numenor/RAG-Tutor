# Kế hoạch dự án: AI Study Assistant (RAG Chatbot + Lộ trình học + Tạo câu hỏi & Tự chấm điểm)

**Mục tiêu:** Xây dựng portfolio project cho vị trí GenAI/LLM Application Developer
**Người thực hiện:** Đạt
**Ngân sách:** 0đ — chỉ dùng free tier / open-source

---

## 1. Mô tả dự án

Chatbot cho phép người dùng upload tài liệu (PDF, docx) và đặt câu hỏi. Chatbot trả lời dựa trên nội dung tài liệu, kèm trích dẫn nguồn (file/trang/đoạn) để tăng độ tin cậy và tránh hallucination.

**Các tính năng mở rộng:**
1. **Sinh câu hỏi ôn tập:** Từ tài liệu đã nạp, hệ thống tự động sinh câu hỏi trắc nghiệm và tự luận để người dùng ôn tập, đồng thời tự chấm điểm bài làm (trắc nghiệm chấm rule-based, tự luận chấm bằng LLM-as-judge có nhận xét chi tiết).
2. **Lộ trình học cá nhân hóa:** Sau khi tài liệu được chunk & embed, hệ thống phân tích và gắn nhãn các chủ đề/khái niệm trong tài liệu, sau đó sinh ra lộ trình học dựa trên mục tiêu điểm số người dùng đặt ra — mục tiêu điểm càng cao, lộ trình càng chi tiết và bao phủ nhiều kiến thức nâng cao hơn.
3. **Nộp bài tự luận bằng ảnh scan:** Ngoài gõ text, người dùng có thể chụp/scan bài làm viết tay hoặc in để nộp, hệ thống tự trích xuất nội dung trước khi chấm.

**Về mặt kỹ thuật (quy mô "tầm trung"):**
- Chunking tự viết (giữ nguyên để thể hiện chiều sâu hiểu biết), tích hợp LangChain làm khung orchestration (vectorstore, retriever, structured output)
- Supabase (Postgres + pgvector) làm database thống nhất cho cả vector lẫn dữ liệu quan hệ
- **Giao diện chuyển từ Streamlit sang ReactJS**, kết nối với backend qua REST API — tách bạch frontend/backend như một ứng dụng web thật, không còn là 1 script Python gộp chung UI và logic

Các tính năng này biến dự án từ "chatbot hỏi-đáp" chung chung thành **AI Study Assistant** hoàn chỉnh — một câu chuyện CV rõ ràng và khác biệt hơn.

---

## 2. Kiến trúc hệ thống

### Tổng quan (mới, do đổi sang React)
```
[React Frontend (Vite)] ⇄ REST API (JSON / multipart) ⇄ [FastAPI Backend]
                                                                ↓
                                    [LangChain orchestration + Gemini API + Supabase]
```

**Nguyên tắc quan trọng:** mọi API key (Gemini, Supabase service key) chỉ nằm ở **backend (FastAPI)**, không bao giờ đưa vào code React — vì code chạy trên trình duyệt luôn có thể bị người dùng xem được (khác với Streamlit trước đây, nơi mọi thứ chạy trên server nên việc này "mặc định an toàn"; giờ tách frontend/backend thì đây là điều phải chủ động đảm bảo).

Hệ thống backend gồm 4 luồng chính, dùng chung phần chunk/embedding ở bước đầu. Mỗi luồng được expose qua các endpoint FastAPI để React gọi vào.

### (a) Luồng nạp tài liệu (nền tảng chung)
```
[User upload file trên React] → POST /documents/upload → [Trích xuất text] → [Chunking tự viết]
                                                                                      ↓
                                                              [Bọc thành LangChain Document]
                                                                                      ↓
                                                        [Embedding: sentence-transformers]
                                                                                      ↓
                              [LangChain SupabaseVectorStore] → [Supabase: Postgres + pgvector]
```

### (b) Luồng chat hỏi-đáp
```
[User gửi câu hỏi trên React] → POST /chat → [Embedding câu hỏi] → [LangChain retriever trên Supabase]
                                                                                ↓
                                                          [LLM sinh câu trả lời + trích dẫn]
                                                                                ↓
                                                    [Trả lời + nguồn] → hiển thị trên React
```

### (c) Luồng sinh lộ trình học cá nhân hóa
```
POST /roadmap/generate → [Chunk trong Supabase] → [LLM: trích xuất & gắn nhãn chủ đề] → [Bảng `topics`]
                    (mỗi chủ đề: mức độ khó, cấp độ Bloom: Nhớ/Hiểu/Áp dụng/Phân tích, chunk liên quan)
                                    ↓
[User đặt mục tiêu điểm trên React] → [Lọc & sắp xếp chủ đề theo mục tiêu] → [Lộ trình học]
                                    ↓
                    Điểm mục tiêu thấp  → chỉ chủ đề cốt lõi, cấp độ Nhớ/Hiểu
                    Điểm mục tiêu TB    → + chủ đề mức Áp dụng
                    Điểm mục tiêu cao   → + chủ đề nâng cao/edge case, cấp độ Phân tích/Đánh giá
```

### (d) Luồng sinh câu hỏi & làm bài
```
POST /questions/generate → [Chunk / chủ đề đã gắn nhãn] → [LLM sinh câu hỏi] → [Bảng `questions`]
                                                          (MCQ + tự luận, kèm đáp án/rubric, gắn chunk nguồn)
                                                                    ↓
[User làm bài trên React]
      ├─ Trắc nghiệm → chọn đáp án → POST /quiz/submit → [Chấm rule-based] → điểm tức thì
      └─ Tự luận  ├─ Gõ text ──────────────────────────────┐
                  └─ Upload ảnh scan → POST /quiz/submit-scan │
                     → [Gemini Vision trích xuất text]        │
                     → trả text về React để user xác nhận/    │
                       chỉnh sửa → gửi lại backend ───────────┤
                                                                ↓
                                          [LLM-as-judge: so với đáp án mẫu/key points]
                                                                ↓
                              [Điểm số + nhận xét + trích dẫn nguồn] → [Bảng `quiz_attempts`]
                                                                ↓
                                                    hiển thị kết quả trên React
```

---

## 3. Thiết kế chunking tự viết + tích hợp LangChain

Quyết định: **tự viết thuật toán chunking** (thay vì dùng thẳng LangChain `RecursiveCharacterTextSplitter`) để hiểu sâu cơ chế RAG và kiểm soát tốt hơn cho văn bản tiếng Việt — nhưng **bọc output thành `Document` object của LangChain** để tương thích với phần còn lại của framework (vectorstore, retriever, chain, structured output parser). Đây là hướng kết hợp: giữ phần "lõi" tự viết, dùng LangChain làm "khung" phía sau.

### Nguyên tắc thiết kế
Luôn cắt tại ranh giới ngữ nghĩa tự nhiên (câu, đoạn) — **không bao giờ** cắt cứng theo số ký tự (kiểu `text[0:1000]`), vì dễ cắt ngang giữa câu/ý, phá vỡ ngữ nghĩa và làm embedding lẫn LLM hiểu sai nội dung.

### Thuật toán (5 bước)

**Bước 1 — Tách theo cấu trúc văn bản trước**
Tách text gốc theo đoạn văn (`\n\n`) và heading nếu phát hiện được (số thứ tự chương/mục, dòng in đậm/viết hoa nếu `pdfplumber` giữ được định dạng).
*Lý do:* đoạn văn thường là 1 đơn vị ý hoàn chỉnh — tách ở đây trước giúp giữ ranh giới ngữ nghĩa tự nhiên nhất.

**Bước 2 — Tách câu trong mỗi đoạn**
Dùng regex tách câu theo dấu `.`, `?`, `!`, có xử lý riêng các trường hợp đặc biệt tiếng Việt: viết tắt ("TP.HCM", "GS.", "TS."), số thập phân ("1.000", "Điều 1.2") để không tách nhầm.
*Lý do:* câu là đơn vị nhỏ nhất an toàn để cắt — không bao giờ cắt giữa câu.

**Bước 3 — Gộp câu theo kiểu "greedy" đến kích thước mục tiêu**
```python
def chunk_sentences(sentences, target_size=500, max_size=700):
    chunks = []
    current = []
    current_len = 0
    for sent in sentences:
        sent_len = len(sent.split())  # đếm theo từ, đơn giản & đủ tốt
        if current_len + sent_len > target_size and current:
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.append(sent)
        current_len += sent_len
    if current:
        chunks.append(" ".join(current))
    return chunks
```
Duyệt qua từng câu, gộp dần vào chunk hiện tại đến khi gần chạm `target_size` thì đóng chunk và bắt đầu chunk mới.
*Lý do dùng greedy:* đơn giản, dễ kiểm soát, đảm bảo chunk có kích thước tương đối đồng đều — tránh chunk siêu ngắn (thiếu ngữ cảnh) hoặc siêu dài (loãng ý).

**Bước 4 — Thêm overlap giữa các chunk**
Lấy 1-2 câu cuối của chunk trước, chèn vào đầu chunk sau.
*Lý do:* nếu không có overlap, thông tin nằm ngay ranh giới 2 chunk có thể bị "gãy" — nửa ở chunk này, nửa ở chunk kia, khiến truy vấn không đủ ngữ cảnh để trả lời chính xác.

**Bước 5 — Gắn metadata & bọc thành LangChain Document**
Lưu kèm: tên file, số trang, section/heading (nếu có), chunk index, vị trí ký tự gốc. Sau đó tạo đối tượng `Document(page_content=chunk_text, metadata={...})` từ `langchain_core.documents`.
*Lý do:* metadata bắt buộc để tính năng trích dẫn nguồn và gắn nhãn chủ đề hoạt động được. Bọc thành `Document` giúp chunk "tự viết" cắm thẳng vào `SupabaseVectorStore` và retriever của LangChain mà không cần viết thêm code tích hợp thủ công.

```python
from langchain_core.documents import Document

def to_langchain_documents(chunks_with_metadata):
    return [
        Document(page_content=c["text"], metadata=c["metadata"])
        for c in chunks_with_metadata
    ]
```

### Vì sao tự viết phần chunking thay vì dùng splitter có sẵn?

**Lý do nên tự viết (cho project CV này):**
- Hiểu rõ cơ chế bên trong — khi phỏng vấn, giải thích được *tại sao* chunk được cắt như vậy, không chỉ nói "tôi dùng LangChain"
- Kiểm soát hoàn toàn logic tách câu tiếng Việt (splitter mặc định của LangChain tối ưu cho tiếng Anh, không xử lý tốt viết tắt/số thập phân kiểu Việt Nam)
- Gắn metadata đúng ý đồ thiết kế (phục vụ trích dẫn + gắn nhãn chủ đề cho lộ trình học) thay vì phải "vá" thêm vào output của thư viện

**Vì sao vẫn dùng LangChain cho phần còn lại:**
- Tránh viết lại code tích hợp Supabase/pgvector thủ công (`SupabaseVectorStore` đã có sẵn, được maintain, xử lý batch insert/query hiệu quả)
- Có sẵn retriever interface, prompt template, structured output parser (hữu ích cho việc ép JSON khi sinh câu hỏi/chấm điểm)
- Dễ tích hợp Gemini qua `langchain_google_genai` mà không cần tự viết wrapper gọi API

**Đánh đổi cần lưu ý (nên ghi vào README):**
- Tốn thời gian test nhiều edge case hơn ở phần chunking tự viết (bảng biểu trong PDF, danh sách gạch đầu dòng ngắn...) mà thư viện đã xử lý sẵn
- Đếm độ dài theo số từ chỉ là ước lượng gần đúng cho số token thực tế
- Dùng LangChain nghĩa là phụ thuộc thêm 1 framework — cần hiểu rõ nó làm gì bên dưới để vẫn trả lời được câu hỏi phỏng vấn về cách retriever/vectorstore hoạt động

---

## 4. Tech stack (100% miễn phí)

| Thành phần | Công cụ | Ghi chú |
|---|---|---|
| Trích xuất PDF | `pdfplumber` | Mã nguồn mở, free |
| Trích xuất Word | `python-docx` | Mã nguồn mở, free |
| Chia chunk | **Tự viết** (xem Mục 3) | Tách theo đoạn → câu → gộp greedy có overlap; bọc thành `Document` của LangChain |
| Framework orchestration | LangChain | `SupabaseVectorStore`, retriever, prompt template, structured output parser, tích hợp Gemini qua `langchain_google_genai` |
| Embedding | `sentence-transformers` (`all-MiniLM-L6-v2`) | Chạy local, miễn phí tuyệt đối, không giới hạn request |
| Vector DB | Supabase (Postgres + extension `pgvector`) | Free tier 500MB DB, không cần thẻ tín dụng; bền vững qua các lần deploy (khác Chroma local) |
| LLM sinh câu trả lời | Gemini 2.5 Flash API | Free tier ~1.500 request/ngày, đủ cho demo |
| **Backend API** | **FastAPI** | Expose REST endpoint cho toàn bộ logic (upload, chat, roadmap, quiz); xử lý CORS để React gọi được |
| **Frontend** | **ReactJS (Vite)** | SPA, gọi backend qua REST API (JSON cho text, multipart cho file/ảnh) |
| Giao tiếp Frontend ↔ Backend | REST API (Axios/fetch), CORS middleware trong FastAPI | API key (Gemini, Supabase) chỉ lưu ở backend, không lộ ra frontend |
| Phân tích & gắn nhãn chủ đề | Gemini 2.5 Flash API | Trích xuất danh sách chủ đề, gắn mức độ khó/cấp độ Bloom; lưu vào bảng `topics` trong Supabase |
| Sinh lộ trình học | Logic lọc/sắp xếp (rule-based) trên bảng `topics` | Không cần thêm thư viện; điều chỉnh độ chi tiết theo mục tiêu điểm user chọn |
| Sinh câu hỏi (MCQ + tự luận) | Gemini 2.5 Flash API, ép output JSON (LangChain structured output parser) | Giới hạn số câu theo số đơn vị kiến thức thực có, tránh bịa đặt/trùng lặp |
| Question bank / lịch sử làm bài / lộ trình | Bảng Postgres trong Supabase (`questions`, `quiz_attempts`, `topics`) | Dùng chung 1 database cho toàn bộ dữ liệu quan hệ |
| Kết nối Supabase | `supabase-py` (client) + LangChain `SupabaseVectorStore` | `supabase-py` cho các bảng quan hệ, LangChain cho phần vector |
| Chấm trắc nghiệm | Rule-based (so sánh đáp án) | Không cần LLM, tức thì, 100% nhất quán |
| Chấm tự luận | Gemini 2.5 Flash API (LLM-as-judge) | So câu trả lời user với đáp án mẫu/key points, trả điểm + nhận xét |
| Nộp bài bằng ảnh scan | Gemini 2.5 Flash API (multimodal/vision) | Gửi ảnh qua endpoint FastAPI, không cần thư viện OCR riêng; luôn cho user xác nhận/sửa text trước khi chấm |
| Deploy Backend | Render free tier (hoặc HuggingFace Spaces bằng Docker) | Free, dễ deploy từ GitHub; lưu ý free tier có thể "ngủ" sau thời gian không hoạt động (cold start request đầu tiên chậm) |
| Deploy Frontend | Vercel hoặc Netlify free tier | Free, deploy React SPA từ GitHub, có HTTPS + custom domain sẵn |

> **Lưu ý:**
> - Rate limit/điều khoản free tier của Gemini có thể thay đổi theo thời gian — kiểm tra lại trên Google AI Studio trước khi build.
> - Project Supabase free tier sẽ **tạm dừng sau 7 ngày không hoạt động** (dữ liệu không mất, chỉ cần kích hoạt lại).
> - Backend Render free tier cũng có thể **spin down khi không có traffic**, khiến request đầu tiên sau thời gian nghỉ bị chậm (cold start) — nên ghi rõ trong README, hoặc cân nhắc ping định kỳ bằng GitHub Actions nếu cần demo luôn nhanh khi phỏng vấn.

---

## 5. Roadmap từng bước

### Bước 1 — Setup Supabase & kiểm tra retrieval (chưa cần LLM)
- [ ] Tạo project Supabase free tier, bật extension `pgvector`
- [ ] Tạo bảng `documents` và `chunks` (cột `embedding` kiểu `vector`) trong Supabase
- [ ] Đọc 1 file PDF mẫu
- [ ] Viết hàm chia chunk tự thiết kế (xem Mục 3): tách đoạn → tách câu (xử lý viết tắt/số thập phân tiếng Việt) → gộp greedy → thêm overlap → gắn metadata
- [ ] Bọc mỗi chunk thành `Document` của LangChain
- [ ] Embed chunk bằng `sentence-transformers`
- [ ] Lưu vào Supabase qua `SupabaseVectorStore` của LangChain
- [ ] Thử 1 câu hỏi, dùng retriever của LangChain để in ra chunk liên quan nhất (test bằng script Python thuần, chưa cần API/UI)
- **Mục tiêu:** xác nhận toàn bộ pipeline chunking tự viết + LangChain + Supabase hoạt động đúng trước khi thêm LLM

### Bước 2 — Thêm LLM sinh câu trả lời
- [ ] Lấy chunk liên quan làm context
- [ ] Ghép context + câu hỏi vào prompt (dùng LangChain prompt template)
- [ ] Gọi Gemini 2.5 Flash API để sinh câu trả lời
- **Mục tiêu:** RAG hoạt động end-to-end lần đầu tiên (vẫn ở dạng script/notebook)

### Bước 3 — Thêm trích dẫn nguồn
- [ ] Lưu metadata cho mỗi chunk (tên file, số trang/đoạn)
- [ ] Hiển thị nguồn kèm mỗi câu trả lời (vd: "Trích từ trang 5, file abc.pdf")
- **Mục tiêu:** tăng độ tin cậy, giảm hallucination — điểm cộng lớn khi phỏng vấn

### Bước 4 — Hỗ trợ nhiều file, nhiều định dạng
- [ ] Cho phép xử lý nhiều PDF/docx cùng lúc
- [ ] Gộp tất cả vào chung bảng `chunks` trong Supabase, phân biệt bằng `document_id`

### Bước 5 — Xây dựng FastAPI backend & giao diện React cho chức năng Chat
- [ ] Khởi tạo project FastAPI, cấu hình CORS cho phép gọi từ React dev server
- [ ] Viết endpoint `POST /documents/upload` (nhận PDF/docx, chạy pipeline chunk → embed → lưu Supabase từ Bước 1-4)
- [ ] Viết endpoint `POST /chat` (nhận câu hỏi, trả lời + trích dẫn nguồn)
- [ ] Khởi tạo project React (Vite), cấu trúc thư mục cơ bản
- [ ] Component upload file, gọi API `/documents/upload`
- [ ] Component khung chat, gọi API `/chat`, hiển thị câu trả lời kèm trích dẫn nguồn
- **Mục tiêu:** có bản demo end-to-end đầu tiên chạy trên trình duyệt qua React, tách biệt rõ frontend/backend

### Bước 6 — Sinh lộ trình học cá nhân hóa
- [ ] Tạo bảng `topics` trong Supabase (chủ đề, mức độ khó, cấp độ Bloom, chunk liên quan)
- [ ] Thiết kế prompt yêu cầu LLM trích xuất danh sách chủ đề/khái niệm từ tài liệu
- [ ] Gắn nhãn mỗi chủ đề: mức độ khó, cấp độ Bloom (Nhớ/Hiểu/Áp dụng/Phân tích/Đánh giá) — lưu vào bảng `topics`
- [ ] Viết endpoint `POST /roadmap/generate` và `GET /roadmap/{document_id}`
- [ ] Viết logic lọc & sắp xếp chủ đề theo mục tiêu: mục tiêu thấp → chỉ chủ đề cốt lõi (Nhớ/Hiểu); mục tiêu cao → thêm chủ đề nâng cao (Áp dụng/Phân tích/Đánh giá)
- [ ] Component React: chọn mục tiêu điểm + hiển thị lộ trình học dạng danh sách chủ đề theo thứ tự gợi ý, kèm chunk/trang liên quan
- **Mục tiêu:** cá nhân hóa độ sâu kiến thức theo mục tiêu của người học, không phải "một lộ trình cho tất cả"

### Bước 7 — Sinh câu hỏi ôn tập từ tài liệu
- [ ] Tạo bảng `questions` trong Supabase (loại câu hỏi, nội dung, đáp án/rubric, chunk nguồn)
- [ ] Thiết kế prompt sinh câu hỏi với ràng buộc JSON schema (mcq + tự luận, dùng LangChain structured output parser), yêu cầu model chỉ dùng nội dung chunk được cung cấp
- [ ] Viết endpoint `POST /questions/generate`
- [ ] Với mỗi chunk/chủ đề, gọi Gemini sinh N câu trắc nghiệm (4 đáp án, 1 đúng) + N câu tự luận (kèm đáp án mẫu/key points)
- [ ] Lưu vào bảng `questions`, gắn mỗi câu hỏi với chunk nguồn để chấm điểm và trích dẫn sau này
- [ ] **Xử lý trường hợp user yêu cầu số câu hỏi vượt quá lượng kiến thức thực có:**
  - [ ] Bước trung gian: yêu cầu LLM liệt kê "đơn vị kiến thức" có trong chunk/chủ đề trước khi sinh câu hỏi
  - [ ] Giới hạn số câu hỏi sinh ra theo số đơn vị kiến thức thực có, không theo số user yêu cầu
  - [ ] Sau khi sinh, so sánh embedding giữa các câu hỏi (`sentence-transformers`) để loại câu hỏi trùng/na ná nhau
  - [ ] Nếu số câu hỏi thực tế ít hơn yêu cầu, trả về lý do rõ ràng trong response API để React hiển thị thông báo cho user
- **Mục tiêu:** có bộ câu hỏi được sinh tự động, bám sát nội dung tài liệu, không bịa đặt, không trùng lặp để "đủ số lượng"

### Bước 8 — Giao diện React làm bài & Tự chấm điểm (kể cả nộp bằng ảnh scan)
- [ ] Tạo bảng `quiz_attempts` trong Supabase (câu hỏi, câu trả lời user, điểm, nhận xét, thời gian nộp, hình thức nộp)
- [ ] Viết endpoint `POST /quiz/submit` (nhận đáp án trắc nghiệm/tự luận dạng text, trả điểm + nhận xét)
- [ ] Viết endpoint `POST /quiz/submit-scan` (nhận ảnh dạng multipart, gọi Gemini Vision trích xuất text, trả text về để user xác nhận trước khi chấm chính thức)
- [ ] Component React tab "Quiz" (tách biệt tab "Chat" và "Lộ trình học"): hiển thị câu trắc nghiệm (radio button), câu tự luận (textarea), nút upload ảnh
- [ ] Component xác nhận/chỉnh sửa text trích xuất từ ảnh trước khi gửi chấm chính thức
- [ ] Hiển thị kết quả (điểm + nhận xét + trích dẫn nguồn) trả về từ backend
- **Mục tiêu:** người dùng ôn tập và nhận phản hồi ngay, kể cả khi đã làm bài ra giấy, không cần người chấm thủ công
- **Lưu ý:** LLM chấm tự luận có thể không hoàn toàn nhất quán giữa các lần chấm, và OCR/vision có thể đọc sai chữ viết tay khó đọc — nên ghi rõ các hạn chế này trong README

### Bước 9 — Cải thiện chất lượng (nâng cao)
- [ ] Semantic chunking thay vì chia cứng theo số ký tự
- [ ] Thêm conversation memory (nhớ ngữ cảnh nhiều lượt hỏi-đáp) — cần lưu session/history ở backend vì React không giữ state qua các lần load lại trang
- [ ] Re-ranking: xếp hạng lại độ liên quan sau khi lấy top-k chunk
- [ ] Xây dashboard tiến độ học tập (component React riêng) từ dữ liệu `quiz_attempts` trong Supabase
- [ ] Streaming response cho chat (Gemini hỗ trợ stream) để trải nghiệm React mượt hơn, giống ChatGPT
- [ ] (Tùy chọn) Gắn quiz checkpoint theo từng chủ đề, yêu cầu đạt điểm tối thiểu mới "mở khóa" chủ đề tiếp theo (gamification kiểu Duolingo)
- [ ] (Tùy chọn) Dùng Supabase Auth để hỗ trợ nhiều người dùng, mỗi người có tài liệu/lộ trình/lịch sử riêng

### Bước 10 — Đánh giá & Deploy
- [ ] Soạn bộ câu hỏi test, đo tỷ lệ trả lời đúng + trích dẫn chính xác
- [ ] (Tùy chọn) Dùng thư viện RAGAS để đánh giá bài bản hơn
- [ ] Deploy backend FastAPI lên Render free tier (hoặc HuggingFace Spaces bằng Docker)
- [ ] Deploy frontend React lên Vercel hoặc Netlify free tier, trỏ về URL backend đã deploy
- [ ] Cấu hình biến môi trường (Supabase URL/key, Gemini API key) an toàn ở backend, không lộ ra bundle React
- [ ] Viết README: vấn đề giải quyết, kiến trúc frontend/backend, demo link, hạn chế (cold start, LLM-as-judge không hoàn toàn nhất quán...)

---

## 6. Định hướng nâng cấp sau MVP (không bắt buộc ngay)

Sau khi MVP chạy ổn, cân nhắc chọn 1 domain cụ thể để có câu chuyện rõ ràng hơn thay vì "chatbot chat với PDF" chung chung, ví dụ:
- Trợ lý tra cứu luật/thuế Việt Nam
- Chatbot hỏi đáp tài liệu học tập (đã một phần thành hiện thực nhờ tính năng lộ trình học + quiz)
- Trợ lý đọc hợp đồng/tài liệu nội bộ

---

## 7. Gợi ý viết cho CV

Ví dụ câu mô tả:
> "Xây dựng AI Study Assistant: ứng dụng full-stack (React + FastAPI) cho phép hỏi-đáp trên tài liệu PDF/docx kèm trích dẫn nguồn (tự viết thuật toán chunking theo ngữ nghĩa, tích hợp LangChain cho retrieval/orchestration); tự động sinh lộ trình học cá nhân hóa theo mục tiêu điểm số; tự sinh câu hỏi trắc nghiệm/tự luận và tự chấm điểm (rule-based cho trắc nghiệm, LLM-as-judge cho tự luận), hỗ trợ nộp bài bằng ảnh scan qua Gemini Vision. Backend: FastAPI + LangChain + Supabase (Postgres/pgvector); Frontend: ReactJS. Deploy backend trên Render, frontend trên Vercel."

Nên có con số cụ thể nếu đo được, ví dụ: % câu trả lời đúng trên bộ test, thời gian phản hồi trung bình, số lượng tài liệu/định dạng hỗ trợ, số câu hỏi sinh ra mỗi tài liệu, độ chính xác OCR trên ảnh scan, độ tương quan giữa điểm LLM chấm và điểm người chấm thủ công (nếu đo thử).

---

## 8. Checklist tổng thể

- [ ] Bước 1: Setup Supabase + retrieval hoạt động (chunking tự viết + LangChain)
- [ ] Bước 2: LLM sinh câu trả lời
- [ ] Bước 3: Trích dẫn nguồn
- [ ] Bước 4: Đa file
- [ ] Bước 5: FastAPI backend + React frontend cho Chat
- [ ] Bước 6: Lộ trình học cá nhân hóa (API + React UI)
- [ ] Bước 7: Sinh câu hỏi ôn tập (có giới hạn theo lượng kiến thức thực có)
- [ ] Bước 8: React UI làm bài & tự chấm điểm (kể cả ảnh scan)
- [ ] Bước 9: Cải thiện chất lượng (tùy chọn)
- [ ] Bước 10: Đánh giá & Deploy (backend + frontend)
- [ ] Viết README + mô tả CV