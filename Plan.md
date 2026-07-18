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
4. **Không gian học nhóm có lời mời:** Mỗi project có owner và member. Owner quản lý tài liệu, lịch chung và lời mời; member được xem tài liệu, chat, làm quiz và tạo annotation riêng.
5. **PDF annotation theo tọa độ:** Người dùng có thể highlight text/vùng chữ nhật trên PDF, chọn màu và thêm ghi chú. Tọa độ được chuẩn hóa để không lệch khi zoom hoặc đổi kích thước màn hình.

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

Hệ thống backend gồm các luồng ingestion/RAG, roadmap, quiz, cộng tác và PDF annotation. Mỗi luồng được expose qua endpoint FastAPI; mọi endpoint đều xác thực Supabase JWT và kiểm tra quyền project ở backend.

### (a) Luồng nạp tài liệu (nền tảng chung)
```
[Owner upload file trên React] → POST /projects/{project_id}/documents → [Tạo document version + ingestion job]
                                                                                      ↓
                                                              [Trích xuất text] → [Chunking tự viết]
                                                                                      ↓
                                                              [Bọc thành LangChain Document]
                                                                                      ↓
                                                        [Embedding multilingual: sentence-transformers]
                                                                                      ↓
                              [RPC match_chunks + pgvector] → [Supabase Postgres + private Storage]
```

### (b) Luồng chat hỏi-đáp
```
[User gửi câu hỏi trên React] → POST /projects/{project_id}/chat/sessions/{session_id}/messages
                                         → [Embedding câu hỏi] → [RPC match_chunks lọc project + document ready]
                                                                                ↓
                                                          [Threshold + rerank → LLM sinh câu trả lời + trích dẫn]
                                                                                ↓
                                                    [Trả lời + nguồn hoặc từ chối khi thiếu bằng chứng]
```

### (c) Luồng sinh lộ trình học cá nhân hóa
```
POST /projects/{project_id}/roadmap/generate → [Chunk trong Supabase] → [LLM trích xuất chủ đề + prerequisite]
                    (mỗi chủ đề: mức độ khó, cấp độ Bloom: Nhớ/Hiểu/Áp dụng/Phân tích, chunk liên quan)
                                    ↓
[Target score + exam date + thời gian học/tuần + diagnostic] → [Xếp thứ tự prerequisite] → [Lộ trình học]
                                    ↓
                    Điểm mục tiêu thấp  → chỉ chủ đề cốt lõi, cấp độ Nhớ/Hiểu
                    Điểm mục tiêu TB    → + chủ đề mức Áp dụng
                    Điểm mục tiêu cao   → + chủ đề nâng cao/edge case, cấp độ Phân tích/Đánh giá
```

### (d) Luồng sinh câu hỏi & làm bài
```
POST /projects/{project_id}/questions/generate → [Chunk/chủ đề] → [LLM sinh câu hỏi] → [Bảng `questions`]
                                                          (MCQ + tự luận, kèm đáp án/rubric, gắn chunk nguồn)
                                                                    ↓
[User bắt đầu quiz session trên React]
      ├─ Trắc nghiệm → chọn đáp án → POST /quiz-sessions/{id}/answers → [Chấm rule-based]
      └─ Tự luận  ├─ Gõ text ──────────────────────────────┐
                  └─ Upload ảnh scan → POST /quiz-sessions/{id}/answers/scan
                     → [Lưu private Storage + Gemini Vision OCR]
                     → trả text về React để user xác nhận/chỉnh sửa
                     → POST /quiz-sessions/{id}/answers/{answer_id}/confirm
                                                                ↓
                                          [LLM-as-judge: so với đáp án mẫu/key points]
                                                                ↓
                              [Điểm + nhận xét + nguồn + model/prompt version] → [`quiz_attempts`]
                                                                ↓
                                                    hiển thị kết quả trên React
```

### (e) Luồng mời thành viên và phân quyền
```
[Owner nhập email] → POST /projects/{id}/invitations → [Lưu token hash + gửi link có hạn]
→ [User đăng nhập, email đã xác minh] → POST /invitations/{token}/accept
→ [Transaction: kiểm tra token/email/expiry → thêm project_members → đánh dấu accepted]
```

### (f) Luồng PDF annotation
```
[PDF.js render document version] → [User chọn text/vùng chữ nhật]
→ POST /document-versions/{id}/annotations
→ [Lưu page_number + rectangles chuẩn hóa 0..1 + selected_text + màu + note]
→ Chỉ chính user được xem/sửa/xóa annotation của mình
```

---

## 3. Thiết kế chunking tự viết + tích hợp LangChain

Quyết định: **tự viết thuật toán chunking** (thay vì dùng thẳng LangChain `RecursiveCharacterTextSplitter`) để hiểu sâu cơ chế RAG và kiểm soát tốt hơn cho văn bản tiếng Việt. Có thể bọc output thành `Document` ở lớp ứng dụng để dùng prompt/retriever interface của LangChain, nhưng persistence và vector search đi qua repository + RPC `match_chunks` tùy biến.

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
def chunk_sentences(sentences, target_tokens=220, max_tokens=256):
    chunks = []
    current = []
    current_len = 0
    for sent in sentences:
        sent_len = count_embedding_tokens(sent)
        if sent_len > max_tokens:
            # Fallback: tách câu quá dài theo clause rồi mới đến token window.
            sentences_to_add = split_long_sentence(sent, max_tokens)
        else:
            sentences_to_add = [sent]
        for item in sentences_to_add:
            item_len = count_embedding_tokens(item)
            if current_len + item_len > target_tokens and current:
                chunks.append(" ".join(current))
                current, current_len = [], 0
            current.append(item)
            current_len += item_len
    if current:
        chunks.append(" ".join(current))
    return chunks
```
Duyệt qua từng câu, đo bằng tokenizer của embedding model và gộp đến `target_tokens`. Câu dài vượt `max_tokens` phải có fallback tách theo mệnh đề/token; không được âm thầm để model truncate phần cuối.
*Lý do dùng greedy:* đơn giản, dễ kiểm soát, đảm bảo chunk có kích thước tương đối đồng đều — tránh chunk siêu ngắn (thiếu ngữ cảnh) hoặc siêu dài (loãng ý).

**Bước 4 — Thêm overlap giữa các chunk**
Lấy 1-2 câu cuối của chunk trước, chèn vào đầu chunk sau.
*Lý do:* nếu không có overlap, thông tin nằm ngay ranh giới 2 chunk có thể bị "gãy" — nửa ở chunk này, nửa ở chunk kia, khiến truy vấn không đủ ngữ cảnh để trả lời chính xác.

**Bước 5 — Gắn metadata & bọc thành LangChain Document**
Lưu kèm: project, document version, tên file, số trang, section/heading, chunk index và `source_spans`. Dùng danh sách span thay cho một cặp offset vì phần overlap có thể đến từ nhiều vùng nguồn. Sau đó có thể tạo `Document(page_content=..., metadata=...)` ở lớp ứng dụng, nhưng việc lưu/truy vấn dùng schema `chunks` và RPC `match_chunks` tùy biến để giữ ràng buộc quan hệ rõ ràng.
*Lý do:* metadata bắt buộc để trích dẫn và gắn nhãn chủ đề hoạt động. Việc tách lớp chuyển đổi `Document` khỏi lớp lưu trữ giúp schema quan hệ vẫn có foreign key/project isolation mà không phụ thuộc schema mặc định của một vectorstore adapter.

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
- Có sẵn prompt template, retriever interface và structured output parser (hữu ích cho việc ép JSON khi sinh câu hỏi/chấm điểm)
- Repository/RPC pgvector vẫn tự viết để kiểm soát filter tenant, document version, threshold và citation metadata
- Dễ tích hợp Gemini qua `langchain_google_genai` mà không cần tự viết wrapper gọi API

**Đánh đổi cần lưu ý (nên ghi vào README):**
- Tốn thời gian test nhiều edge case hơn ở phần chunking tự viết (bảng biểu trong PDF, danh sách gạch đầu dòng ngắn...) mà thư viện đã xử lý sẵn
- Tokenizer và giới hạn chunk phụ thuộc embedding model; mọi thay đổi model phải tạo document version và re-embed thay vì trộn vector khác phiên bản
- Dùng LangChain nghĩa là phụ thuộc thêm 1 framework — cần hiểu rõ nó làm gì bên dưới để vẫn trả lời được câu hỏi phỏng vấn về cách retriever/vectorstore hoạt động

---

## 4. Tech stack (free-tier-first cho portfolio/demo)

| Thành phần | Công cụ | Ghi chú |
|---|---|---|
| Trích xuất PDF | `pdfplumber` | Mã nguồn mở, free |
| Trích xuất Word | `python-docx` | Mã nguồn mở, free |
| Chia chunk | **Tự viết** (xem Mục 3) | Tách theo đoạn → câu → gộp greedy có overlap; bọc thành `Document` của LangChain |
| Framework orchestration | LangChain | Prompt template, retriever abstraction, structured output và tích hợp Gemini; không phụ thuộc `SupabaseVectorStore` cho persistence |
| Embedding | `sentence-transformers` multilingual 384 chiều (baseline: `paraphrase-multilingual-MiniLM-L12-v2`) | Phù hợp tài liệu tiếng Việt; model cuối cùng phải được chọn bằng benchmark retrieval, không chọn chỉ theo độ phổ biến |
| Vector DB | Supabase Postgres + `pgvector` + RPC `match_chunks` | Filter theo project/document version ngay trong SQL, có similarity threshold; dùng HNSW sau khi có dữ liệu benchmark |
| LLM sinh câu trả lời | Gemini Flash model ổn định được cấu hình bằng environment | Không hard-code quota/model alias trong plan; kiểm tra model và rate limit hiện hành trước deploy |
| **Backend API** | **FastAPI** | Expose REST endpoint cho toàn bộ logic (upload, chat, roadmap, quiz); xử lý CORS để React gọi được |
| **Frontend** | **ReactJS (Vite)** | SPA, gọi backend qua REST API (JSON cho text, multipart cho file/ảnh) |
| Giao tiếp Frontend ↔ Backend | REST API (Axios/fetch), CORS middleware trong FastAPI | API key (Gemini, Supabase) chỉ lưu ở backend, không lộ ra frontend |
| Phân tích & gắn nhãn chủ đề | Gemini Flash + structured output | Trích xuất topic, nguồn và prerequisite; lưu model/prompt version |
| Sinh lộ trình học | Rule-based trên topics/prerequisites + diagnostic/time constraints | Target score không phải đầu vào duy nhất |
| Sinh câu hỏi (MCQ + tự luận) | Gemini Flash + LangChain structured output | Giới hạn theo knowledge units, source chunks và dedup embedding |
| Question bank / lịch sử / lộ trình | Schema Postgres v5 | Quiz session, attempt snapshot và review state tách riêng |
| Kết nối Supabase | `supabase-py` + repository/RPC tùy biến | Không giả định schema mặc định của `SupabaseVectorStore`; LangChain vẫn dùng cho prompt, structured output và orchestration |
| Auth & phân quyền | Supabase Auth + RLS + FastAPI JWT verification | Auth/RLS là bắt buộc trong MVP; service key chỉ dùng cho tác vụ hệ thống và backend vẫn phải kiểm tra membership |
| Lưu file | Supabase Storage private buckets | PDF/docx và ảnh bài viết tay không public; truy cập qua signed URL ngắn hạn |
| PDF viewer | PDF.js | Render PDF, text selection và rectangles chuẩn hóa cho annotation |
| Chấm trắc nghiệm | Rule-based (so sánh đáp án) | Không cần LLM, tức thì, 100% nhất quán |
| Chấm tự luận | Gemini Flash (LLM-as-judge) | Chấm theo rubric + evidence, lưu model/prompt version; không chỉ so với đáp án mẫu |
| Nộp bài bằng ảnh scan | Gemini multimodal/vision | Lưu private, OCR trước, bắt buộc user xác nhận/sửa text rồi mới chấm |
| Deploy Backend | Render free tier (hoặc HuggingFace Spaces bằng Docker) | Free, dễ deploy từ GitHub; lưu ý free tier có thể "ngủ" sau thời gian không hoạt động (cold start request đầu tiên chậm) |
| Deploy Frontend | Vercel hoặc Netlify free tier | Free, deploy React SPA từ GitHub, có HTTPS + custom domain sẵn |

> **Lưu ý:**
> - Rate limit/điều khoản free tier của Gemini có thể thay đổi theo thời gian — kiểm tra lại trên Google AI Studio trước khi build.
> - Project Supabase free tier sẽ **tạm dừng sau 7 ngày không hoạt động** (dữ liệu không mất, chỉ cần kích hoạt lại).
> - Backend Render free tier có thể spin down khi không có traffic; không dùng process FastAPI làm cron/scheduler đáng tin cậy và cần ghi rõ cold start trong README.

---

## 5. Roadmap MVP từng bước

### Bước 1 — Schema, Auth, RLS và Storage
- [ ] Tạo migration theo `Database_design_plan.md` v5; bật `pgvector` và tạo private buckets cho tài liệu/ảnh bài làm.
- [ ] Tích hợp Supabase Auth email/password, xác minh JWT trong FastAPI và tạo owner membership cùng transaction khi tạo project.
- [ ] Hoàn thiện RLS cho mọi bảng; thêm integration test chứng minh user ngoài project không đọc/ghi được dữ liệu.
- [ ] Khóa quyền MVP: owner quản lý file, câu hỏi, lịch và invitation; member xem tài liệu, chat, làm quiz và CRUD annotation riêng.
- **Mục tiêu:** nền tảng multi-user an toàn trước khi thêm dữ liệu học tập.

### Bước 2 — Ingestion, document versioning và retrieval
- [ ] Upload PDF/docx vào Storage private; lưu checksum, MIME thực, kích thước và tạo `document_versions` + `ingestion_jobs`.
- [ ] Xử lý bất đồng bộ extract → chunk theo tokenizer → embed multilingual → summary; retry phải idempotent.
- [ ] Viết RPC `match_chunks` lọc theo project, version đang active và document `ready`; thêm similarity threshold.
- [ ] Benchmark ít nhất hai cấu hình embedding/chunk trên bộ câu hỏi tiếng Việt trước khi chốt model.
- **Mục tiêu:** upload có progress/retry và retrieval không bao giờ lẫn project.

### Bước 3 — RAG chat có citation và abstain
- [ ] Tạo chat session/history, multi-document retrieval trong phạm vi project và streaming response.
- [ ] Mỗi citation chứa chunk, document version, file, trang và source spans để UI mở đúng nguồn.
- [ ] Nếu không có evidence vượt threshold, trả trạng thái `insufficient_evidence` thay vì để LLM đoán.
- [ ] Đo retrieval recall, answer correctness, citation correctness và latency trên test set cố định.
- **Mục tiêu:** vertical slice RAG chạy end-to-end và có số liệu đánh giá.

### Bước 4 — Group invitation
- [ ] Owner tạo/hủy/liệt kê invitation; mỗi project/email chỉ có một invitation pending.
- [ ] Chỉ lưu token hash; link có expiry. Accept yêu cầu user đăng nhập và email đã xác minh trùng email được mời.
- [ ] Accept invitation chạy transaction: khóa invitation → kiểm tra status/expiry/email → insert membership → đánh dấu accepted.
- **Mục tiêu:** chia sẻ project an toàn mà member không có quyền quản trị nội dung chung.

### Bước 5 — PDF viewer và annotation tọa độ
- [ ] Dùng PDF.js render đúng `document_version` và text layer.
- [ ] Hỗ trợ highlight text/vùng chữ nhật, màu, note và CRUD annotation.
- [ ] Lưu page number, selected text và danh sách rectangle chuẩn hóa `0..1`; annotation luôn riêng theo user.
- [ ] Khi có version mới, annotation cũ tiếp tục mở version cũ và không tự map tọa độ.
- **Mục tiêu:** annotation giữ đúng vị trí sau reload, zoom và resize.

### Bước 6 — Topics, roadmap và lịch học
- [ ] Trích xuất topics, nguồn và prerequisite từ chunks của project.
- [ ] Roadmap nhận target score, exam date, thời gian học/tuần và diagnostic score; không suy ra độ sâu chỉ từ target score.
- [ ] AI schedule có trạng thái `suggested/accepted/rejected`; completion được lưu riêng từng user.
- **Mục tiêu:** lộ trình có thứ tự prerequisite và phù hợp thời gian thực tế.

### Bước 7 — Question bank và quiz sessions
- [ ] Sinh MCQ/tự luận bằng structured output; mỗi question có source chunks, rubric, model/prompt version và trạng thái version.
- [ ] Giới hạn số câu theo knowledge units, loại trùng bằng embedding và trả lý do nếu sinh ít hơn yêu cầu.
- [ ] Tạo `quiz_sessions` để nhóm câu hỏi thành một lần làm bài; `quiz_attempts` lưu từng câu và snapshot nội dung/rubric.
- [ ] MCQ chấm rule-based; tự luận chấm theo rubric + evidence, không chỉ so với model answer.
- **Mục tiêu:** tổng điểm/lịch sử vẫn đúng khi question hoặc document có version mới.

### Bước 8 — Chấm bài viết tay
- [ ] Upload JPEG/PNG/WebP đã kiểm tra MIME và dung lượng vào Storage private theo user/project/attempt.
- [ ] Luồng bắt buộc hai bước: OCR → user xác nhận/sửa text → chấm chính thức.
- [ ] Lưu OCR raw, confirmed text, model/prompt version, điểm, feedback và vùng OCR không chắc chắn.
- [ ] Xem lại bằng signed URL ngắn hạn; user có thể xóa ảnh nhưng giữ text/kết quả nếu muốn.
- **Mục tiêu:** ảnh không public, retry không tạo file/attempt trùng và không chấm trước khi xác nhận OCR.

### Bước 9 — Spaced repetition và progress
- [ ] Mỗi user-question có một `review_state` duy nhất gồm due date, interval, repetitions và ease factor.
- [ ] Tính danh sách đến hạn khi user mở app hoặc bằng scheduler hỗ trợ thật; không phụ thuộc cron trong process FastAPI free-tier.
- [ ] Ghi activity thô; `progress_snapshots` là aggregate idempotent có thể rebuild.
- [ ] Dashboard hiển thị điểm, tỷ lệ đúng theo topic, streak/activity và lịch ôn đến hạn.
- **Mục tiêu:** không tạo lịch ôn trùng và số liệu dashboard có nguồn rõ ràng.

### Bước 10 — Hardening, đánh giá và deploy
- [ ] Rate limit/quota cho Gemini; log request ID, job ID, model, prompt version, latency và lỗi nhưng không log nội dung nhạy cảm mặc định.
- [ ] Test authorization, file validation, signed URL, retry/idempotency, RAG evaluation, OCR và grading consistency.
- [ ] Deploy frontend/backend; ghi rõ cold start, quota free tier và giới hạn LLM/OCR trong README.
- [ ] Export PDF, XP/checkpoint và chia sẻ annotation giữa thành viên để sau MVP.

---

## 6. Định hướng nâng cấp sau MVP (không bắt buộc ngay)

Sau khi MVP chạy ổn, cân nhắc chọn 1 domain cụ thể để có câu chuyện rõ ràng hơn thay vì "chatbot chat với PDF" chung chung, ví dụ:
- Trợ lý tra cứu luật/thuế Việt Nam
- Chatbot hỏi đáp tài liệu học tập (đã một phần thành hiện thực nhờ tính năng lộ trình học + quiz)
- Trợ lý đọc hợp đồng/tài liệu nội bộ

---

## 7. Gợi ý viết cho CV

Ví dụ câu mô tả:
> "Xây dựng AI Study Assistant multi-user bằng React + FastAPI: RAG đa tài liệu tiếng Việt có trích dẫn và cơ chế từ chối khi thiếu bằng chứng; ingestion bất đồng bộ có versioning; mời nhóm học với RLS; PDF annotation theo tọa độ; sinh quiz, chấm tự luận/ảnh viết tay qua luồng OCR xác nhận; spaced repetition và progress dashboard. Backend dùng Supabase Auth/Postgres/pgvector/Storage, RPC retrieval tùy biến và LangChain cho orchestration/structured output."

Nên có con số cụ thể nếu đo được, ví dụ: % câu trả lời đúng trên bộ test, thời gian phản hồi trung bình, số lượng tài liệu/định dạng hỗ trợ, số câu hỏi sinh ra mỗi tài liệu, độ chính xác OCR trên ảnh scan, độ tương quan giữa điểm LLM chấm và điểm người chấm thủ công (nếu đo thử).

---

## 8. Checklist tổng thể

- [ ] Bước 1: Schema v5 + Auth + RLS + private Storage
- [ ] Bước 2: Ingestion jobs + document versioning + multilingual retrieval
- [ ] Bước 3: Multi-document RAG + citation + abstain + evaluation
- [ ] Bước 4: Group invitation bảo mật bằng token hash và verified email
- [ ] Bước 5: PDF.js annotation highlight/note theo tọa độ chuẩn hóa
- [ ] Bước 6: Topics + prerequisite + roadmap + lịch học
- [ ] Bước 7: Question bank + quiz sessions + grading có version
- [ ] Bước 8: Ảnh viết tay private + OCR confirmation + quyền xóa ảnh
- [ ] Bước 9: Review states + progress dashboard có thể rebuild
- [ ] Bước 10: Hardening + đánh giá + deploy + README/CV

### Tiêu chí MVP hoàn thành
- [ ] User ngoài project không thể đọc/ghi dữ liệu hoặc file của project bằng cả FastAPI và Supabase API.
- [ ] Member chỉ học và CRUD annotation riêng; owner mới quản lý tài liệu, lịch chung, question generation và invitation.
- [ ] Retrieval không trả chunk chéo project và trả `insufficient_evidence` khi nguồn không đủ.
- [ ] Annotation không lệch sau reload/zoom/resize và không mất khi document có version mới.
- [ ] Ảnh bài viết tay chỉ truy cập qua signed URL; bắt buộc xác nhận OCR trước khi chấm và có thể xóa ảnh.
- [ ] Lịch sử quiz/review/progress không bị thay đổi khi tài liệu hoặc câu hỏi có version mới.
