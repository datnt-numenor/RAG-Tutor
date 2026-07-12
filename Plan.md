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

Các tính năng này biến dự án từ "chatbot hỏi-đáp" chung chung thành **AI Study Assistant** hoàn chỉnh — một câu chuyện CV rõ ràng và khác biệt hơn.

---

## 2. Kiến trúc hệ thống

Hệ thống gồm 4 luồng chính, dùng chung phần chunk/embedding ở bước đầu.

### (a) Luồng nạp tài liệu (nền tảng chung)
```
[File PDF/docx] → [Trích xuất text] → [Chia chunk] → [Embedding] → [Vector DB]
```

### (b) Luồng chat hỏi-đáp
```
[Câu hỏi user] → [Embedding câu hỏi] → [Tìm chunk liên quan nhất] → [LLM sinh câu trả lời + trích dẫn] → [Trả lời + nguồn]
```

### (c) Luồng sinh lộ trình học cá nhân hóa
```
[Vector DB] → [LLM: trích xuất & gắn nhãn chủ đề]
                    (mỗi chủ đề: mức độ khó, cấp độ Bloom: Nhớ/Hiểu/Áp dụng/Phân tích, chunk liên quan)
                                    ↓
[User đặt mục tiêu điểm] → [Lọc & sắp xếp chủ đề theo mục tiêu] → [Lộ trình học]
                                    ↓
                    Điểm mục tiêu thấp  → chỉ chủ đề cốt lõi, cấp độ Nhớ/Hiểu
                    Điểm mục tiêu TB    → + chủ đề mức Áp dụng
                    Điểm mục tiêu cao   → + chủ đề nâng cao/edge case, cấp độ Phân tích/Đánh giá
```

### (d) Luồng sinh câu hỏi & làm bài
```
[Vector DB / chủ đề đã gắn nhãn] → [LLM sinh câu hỏi] → [Question Bank]
                                                          (MCQ + tự luận, kèm đáp án/rubric, gắn chunk nguồn)
                                                                    ↓
[User làm bài]
      ├─ Trắc nghiệm → chọn đáp án → [Chấm rule-based] → điểm tức thì
      └─ Tự luận  ├─ Gõ text ────────────────────────┐
                  └─ Upload ảnh scan → [Gemini Vision  │
                     trích xuất text] → [User xác nhận/ │
                     chỉnh sửa text] ────────────────────┤
                                                          ↓
                                          [LLM-as-judge: so với đáp án mẫu/key points]
                                                          ↓
                                          [Điểm số + nhận xét + trích dẫn nguồn]
```

---

## 3. Thiết kế chunking tự viết (không dùng thư viện)

Quyết định: **tự viết thuật toán chunking** thay vì dùng LangChain `RecursiveCharacterTextSplitter`, để hiểu sâu cơ chế RAG và kiểm soát tốt hơn cho văn bản tiếng Việt.

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

**Bước 5 — Gắn metadata cho từng chunk**
Lưu kèm: tên file, số trang, section/heading (nếu có), chunk index, vị trí ký tự gốc.
*Lý do:* bắt buộc để tính năng trích dẫn nguồn (Bước 3 roadmap) và gắn nhãn chủ đề (Bước 6 roadmap) hoạt động được.

### Vì sao tự viết thay vì dùng LangChain splitter?

**Lý do nên tự viết (cho project CV này):**
- Hiểu rõ cơ chế bên trong — khi phỏng vấn, giải thích được *tại sao* chunk được cắt như vậy, không chỉ nói "tôi dùng LangChain"
- Kiểm soát hoàn toàn logic tách câu tiếng Việt (splitter mặc định của LangChain tối ưu cho tiếng Anh, không xử lý tốt viết tắt/số thập phân kiểu Việt Nam)
- Gắn metadata đúng ý đồ thiết kế (phục vụ trích dẫn + gắn nhãn chủ đề cho lộ trình học) thay vì phải "vá" thêm vào output của thư viện

**Đánh đổi cần lưu ý (nên ghi vào README, thể hiện tư duy trung thực về hạn chế):**
- Tốn thời gian test nhiều edge case hơn (bảng biểu trong PDF, danh sách gạch đầu dòng ngắn, văn bản không có dấu câu rõ ràng...) mà thư viện đã xử lý sẵn qua nhiều năm
- Đếm độ dài theo số từ chỉ là ước lượng gần đúng cho số token thực tế — nếu cần chính xác hơn phải dùng tokenizer thật (thêm dependency), nhưng với project portfolio mức ước lượng này đủ dùng

---

## 4. Tech stack (100% miễn phí)

| Thành phần | Công cụ | Ghi chú |
|---|---|---|
| Trích xuất PDF | `pdfplumber` | Mã nguồn mở, free |
| Trích xuất Word | `python-docx` | Mã nguồn mở, free |
| Chia chunk | **Tự viết** (xem Mục 3) | Tách theo đoạn → câu → gộp greedy có overlap; kiểm soát tốt hơn cho tiếng Việt so với thư viện có sẵn |
| Embedding | `sentence-transformers` (`all-MiniLM-L6-v2`) | Chạy local, miễn phí tuyệt đối, không giới hạn request |
| Vector DB | Chroma | Local, dễ dùng, free |
| LLM sinh câu trả lời | Gemini 2.5 Flash API | Free tier ~1.500 request/ngày, đủ cho demo |
| Giao diện | Streamlit | Free, code ít, lên UI chat/quiz/roadmap nhanh |
| Phân tích & gắn nhãn chủ đề | Gemini 2.5 Flash API | Trích xuất danh sách chủ đề, gắn mức độ khó/cấp độ Bloom cho từng chủ đề |
| Sinh lộ trình học | Logic lọc/sắp xếp (rule-based) trên kết quả gắn nhãn ở trên | Không cần thêm thư viện; điều chỉnh độ chi tiết theo mục tiêu điểm user chọn |
| Sinh câu hỏi (MCQ + tự luận) | Gemini 2.5 Flash API, ép output dạng JSON | Prompt yêu cầu model chỉ dùng nội dung chunk, tránh bịa câu hỏi ngoài tài liệu; giới hạn số câu theo số đơn vị kiến thức thực có |
| Question bank | JSON file hoặc SQLite | Lưu câu hỏi kèm đáp án/rubric + chunk nguồn để chấm điểm & trích dẫn |
| Chấm trắc nghiệm | Rule-based (so sánh đáp án) | Không cần LLM, tức thì, 100% nhất quán |
| Chấm tự luận | Gemini 2.5 Flash API (LLM-as-judge) | So câu trả lời user với đáp án mẫu/key points, trả điểm + nhận xét |
| Nộp bài bằng ảnh scan | Gemini 2.5 Flash API (multimodal/vision) | Gửi ảnh trực tiếp cho Gemini để trích xuất text, không cần thư viện OCR riêng (Tesseract/EasyOCR); luôn cho user xác nhận/sửa text trước khi chấm |
| Deploy | Streamlit Community Cloud / HuggingFace Spaces | Free, có link demo public |

> **Lưu ý:** Rate limit/điều khoản free tier của Gemini có thể thay đổi theo thời gian — kiểm tra lại trên Google AI Studio trước khi build để chắc chắn số liệu mới nhất.

---

## 5. Roadmap từng bước

### Bước 1 — Kiểm tra retrieval (chưa cần LLM)
- [ ] Đọc 1 file PDF mẫu
- [ ] Viết hàm chia chunk tự thiết kế (xem Mục 3): tách đoạn → tách câu (xử lý viết tắt/số thập phân tiếng Việt) → gộp greedy → thêm overlap → gắn metadata
- [ ] Embed chunk bằng `sentence-transformers`
- [ ] Lưu vào Chroma
- [ ] Thử 1 câu hỏi, in ra chunk liên quan nhất
- **Mục tiêu:** xác nhận cả việc chia chunk lẫn "tìm đúng đoạn văn bản" hoạt động tốt trước khi thêm LLM

### Bước 2 — Thêm LLM sinh câu trả lời
- [ ] Lấy chunk liên quan làm context
- [ ] Ghép context + câu hỏi vào prompt
- [ ] Gọi Gemini 2.5 Flash API để sinh câu trả lời
- **Mục tiêu:** RAG hoạt động end-to-end lần đầu tiên

### Bước 3 — Thêm trích dẫn nguồn
- [ ] Lưu metadata cho mỗi chunk (tên file, số trang/đoạn)
- [ ] Hiển thị nguồn kèm mỗi câu trả lời (vd: "Trích từ trang 5, file abc.pdf")
- **Mục tiêu:** tăng độ tin cậy, giảm hallucination — điểm cộng lớn khi phỏng vấn

### Bước 4 — Hỗ trợ nhiều file, nhiều định dạng
- [ ] Cho phép upload nhiều PDF/docx cùng lúc
- [ ] Gộp tất cả vào chung 1 vector DB, phân biệt bằng metadata

### Bước 5 — Giao diện chat với Streamlit
- [ ] Khu vực upload file
- [ ] Khung chat hỏi-đáp
- [ ] Hiển thị nguồn trích dẫn dưới mỗi câu trả lời

### Bước 6 — Sinh lộ trình học cá nhân hóa
- [ ] Thiết kế prompt yêu cầu LLM trích xuất danh sách chủ đề/khái niệm từ tài liệu
- [ ] Gắn nhãn mỗi chủ đề: mức độ khó, cấp độ Bloom (Nhớ/Hiểu/Áp dụng/Phân tích/Đánh giá), chunk liên quan
- [ ] Thêm UI cho user chọn mục tiêu điểm (vd: thang điểm hoặc mức Cơ bản/Khá/Giỏi)
- [ ] Viết logic lọc & sắp xếp chủ đề theo mục tiêu: mục tiêu thấp → chỉ chủ đề cốt lõi (Nhớ/Hiểu); mục tiêu cao → thêm chủ đề nâng cao (Áp dụng/Phân tích/Đánh giá)
- [ ] Hiển thị lộ trình học dạng danh sách các chủ đề theo thứ tự gợi ý, kèm chunk/trang liên quan để đọc
- **Mục tiêu:** cá nhân hóa độ sâu kiến thức theo mục tiêu của người học, không phải "một lộ trình cho tất cả"

### Bước 7 — Sinh câu hỏi ôn tập từ tài liệu
- [ ] Thiết kế prompt sinh câu hỏi với ràng buộc JSON schema (mcq + tự luận), yêu cầu model chỉ dùng nội dung chunk được cung cấp
- [ ] Với mỗi chunk/chủ đề, gọi Gemini sinh N câu trắc nghiệm (4 đáp án, 1 đúng) + N câu tự luận (kèm đáp án mẫu/key points)
- [ ] Lưu question bank (JSON hoặc SQLite), gắn mỗi câu hỏi với chunk nguồn để chấm điểm và trích dẫn sau này
- [ ] Cho người dùng chọn phạm vi tạo câu hỏi (toàn bộ tài liệu / theo chủ đề trong lộ trình học)
- [ ] **Xử lý trường hợp user yêu cầu số câu hỏi vượt quá lượng kiến thức thực có:**
  - [ ] Bước trung gian: yêu cầu LLM liệt kê "đơn vị kiến thức" (khái niệm/sự kiện/quan hệ) có trong chunk/chủ đề trước khi sinh câu hỏi
  - [ ] Giới hạn số câu hỏi sinh ra theo số đơn vị kiến thức thực có, không theo số user yêu cầu
  - [ ] Sau khi sinh, so sánh embedding giữa các câu hỏi (dùng lại `sentence-transformers`) để phát hiện và loại câu hỏi trùng/na ná nhau
  - [ ] Nếu số câu hỏi thực tế ít hơn yêu cầu, hiển thị thông báo rõ lý do + gợi ý mở rộng phạm vi (chọn nhiều chunk/chủ đề hơn) thay vì im lặng cắt bớt
- **Mục tiêu:** có bộ câu hỏi được sinh tự động, bám sát nội dung tài liệu, không bịa đặt, không trùng lặp để "đủ số lượng"

### Bước 8 — Giao diện làm bài & Tự chấm điểm (kể cả nộp bằng ảnh scan)
- [ ] Thêm tab "Quiz" trong Streamlit, tách biệt với tab "Chat" và tab "Lộ trình học"
- [ ] Hiển thị câu trắc nghiệm (radio button) và câu tự luận (text area)
- [ ] Thêm tùy chọn nộp bài tự luận bằng ảnh scan/chụp thay vì gõ text
- [ ] Gửi ảnh cho Gemini Vision để trích xuất nội dung, hiển thị lại cho user xác nhận/chỉnh sửa trước khi chấm
- [ ] Chấm trắc nghiệm: so sánh đáp án chọn với đáp án đúng — rule-based, hiển thị kết quả tức thì
- [ ] Chấm tự luận: gọi LLM đóng vai giám khảo (LLM-as-judge) — so câu trả lời (gõ tay hoặc trích từ ảnh) với đáp án mẫu/key points, trả về điểm số + nhận xét (đã đúng ý nào, thiếu ý nào)
- [ ] Hiển thị kết quả kèm trích dẫn lại đoạn tài liệu liên quan
- **Mục tiêu:** người dùng ôn tập và nhận phản hồi ngay, kể cả khi đã làm bài ra giấy, không cần người chấm thủ công
- **Lưu ý:** LLM chấm tự luận có thể không hoàn toàn nhất quán giữa các lần chấm, và OCR/vision có thể đọc sai chữ viết tay khó đọc — nên ghi rõ các hạn chế này trong README, đây cũng là điểm thú vị để bàn luận trong phỏng vấn về đánh giá LLM output

### Bước 9 — Cải thiện chất lượng (nâng cao)
- [ ] Semantic chunking thay vì chia cứng theo số ký tự
- [ ] Thêm conversation memory (nhớ ngữ cảnh nhiều lượt hỏi-đáp)
- [ ] Re-ranking: xếp hạng lại độ liên quan sau khi lấy top-k chunk
- [ ] Lưu lịch sử làm bài (SQLite) để theo dõi tiến bộ qua thời gian — thêm góc nhìn "learning progress dashboard"
- [ ] (Tùy chọn) Gắn quiz checkpoint theo từng chủ đề trong lộ trình học, yêu cầu đạt điểm tối thiểu mới "mở khóa" chủ đề tiếp theo (gamification kiểu Duolingo)

### Bước 10 — Đánh giá & Deploy
- [ ] Soạn bộ câu hỏi test, đo tỷ lệ trả lời đúng + trích dẫn chính xác
- [ ] (Tùy chọn) Dùng thư viện RAGAS để đánh giá bài bản hơn
- [ ] Deploy lên Streamlit Cloud hoặc HuggingFace Spaces
- [ ] Viết README: vấn đề giải quyết, kiến trúc, demo link, hạn chế

---

## 6. Định hướng nâng cấp sau MVP (không bắt buộc ngay)

Sau khi MVP chạy ổn, cân nhắc chọn 1 domain cụ thể để có câu chuyện rõ ràng hơn thay vì "chatbot chat với PDF" chung chung, ví dụ:
- Trợ lý tra cứu luật/thuế Việt Nam
- Chatbot hỏi đáp tài liệu học tập (đã một phần thành hiện thực nhờ tính năng lộ trình học + quiz)
- Trợ lý đọc hợp đồng/tài liệu nội bộ

---

## 7. Gợi ý viết cho CV

Ví dụ câu mô tả:
> "Xây dựng AI Study Assistant: RAG chatbot cho phép hỏi-đáp trên tài liệu PDF/docx kèm trích dẫn nguồn (tự viết thuật toán chunking theo ngữ nghĩa, không dùng thư viện có sẵn); tự động sinh lộ trình học cá nhân hóa theo mục tiêu điểm số; tự sinh câu hỏi trắc nghiệm/tự luận và tự chấm điểm (rule-based cho trắc nghiệm, LLM-as-judge cho tự luận), hỗ trợ nộp bài bằng ảnh scan qua Gemini Vision. Stack: sentence-transformers + Chroma cho retrieval, Gemini API cho sinh nội dung, phân tích chủ đề và chấm điểm. Deploy public demo trên Streamlit Cloud."

Nên có con số cụ thể nếu đo được, ví dụ: % câu trả lời đúng trên bộ test, thời gian phản hồi trung bình, số lượng tài liệu/định dạng hỗ trợ, số câu hỏi sinh ra mỗi tài liệu, độ chính xác OCR trên ảnh scan, độ tương quan giữa điểm LLM chấm và điểm người chấm thủ công (nếu đo thử).

---

## 8. Checklist tổng thể

- [ ] Bước 1: Retrieval hoạt động (bao gồm chunking tự viết)
- [ ] Bước 2: LLM sinh câu trả lời
- [ ] Bước 3: Trích dẫn nguồn
- [ ] Bước 4: Đa file
- [ ] Bước 5: Giao diện Streamlit
- [ ] Bước 6: Lộ trình học cá nhân hóa
- [ ] Bước 7: Sinh câu hỏi ôn tập (có giới hạn theo lượng kiến thức thực có)
- [ ] Bước 8: Giao diện làm bài & tự chấm điểm (kể cả ảnh scan)
- [ ] Bước 9: Cải thiện chất lượng (tùy chọn)
- [ ] Bước 10: Đánh giá & Deploy
- [ ] Viết README + mô tả CV