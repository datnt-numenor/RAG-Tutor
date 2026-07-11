# Kế hoạch dự án: AI Study Assistant (RAG Chatbot + Tạo câu hỏi & Tự chấm điểm)

**Mục tiêu:** Xây dựng portfolio project cho vị trí GenAI/LLM Application Developer
**Người thực hiện:** Đạt
**Ngân sách:** 0đ — chỉ dùng free tier / open-source

---

## 1. Mô tả dự án

Chatbot cho phép người dùng upload tài liệu (PDF, docx) và đặt câu hỏi. Chatbot trả lời dựa trên nội dung tài liệu, kèm trích dẫn nguồn (file/trang/đoạn) để tăng độ tin cậy và tránh hallucination.

**Tính năng mở rộng:** Từ tài liệu đã nạp, hệ thống tự động sinh câu hỏi trắc nghiệm và tự luận để người dùng ôn tập, đồng thời tự chấm điểm bài làm (trắc nghiệm chấm rule-based, tự luận chấm bằng LLM-as-judge có nhận xét chi tiết). Tính năng này biến dự án từ "chatbot hỏi-đáp" chung chung thành **AI Study Assistant** — một câu chuyện CV rõ ràng và khác biệt hơn.

---

## 2. Kiến trúc hệ thống

```
[File PDF/docx] → [Trích xuất text] → [Chia chunk] → [Embedding] → [Vector DB]
                                                          ↓                ↓
                                          [LLM sinh câu hỏi]      [Câu hỏi user]
                                                          ↓                ↓
                                          [Question Bank]    [Tìm chunk liên quan nhất]
                                          (MCQ + tự luận,             ↓
                                           kèm đáp án/rubric   [LLM sinh câu trả lời + trích dẫn]
                                           + nguồn chunk)             ↓
                                                          ↓      [Trả lời + nguồn]
                                          [Giao diện Quiz]
                                                          ↓
                                          [User nộp bài làm]
                                                  ↓                    ↓
                                    [Chấm trắc nghiệm]      [Chấm tự luận]
                                    (so đáp án, rule-based)  (LLM-as-judge:
                                                              so với đáp án mẫu
                                                              → điểm + nhận xét)
```

**Luồng hoạt động (chat):**
1. Người dùng upload tài liệu
2. Hệ thống trích xuất text, chia thành các đoạn nhỏ (chunk)
3. Mỗi chunk được chuyển thành vector (embedding) và lưu vào vector database
4. Khi người dùng hỏi, câu hỏi cũng được embed, hệ thống tìm các chunk có nội dung gần nghĩa nhất
5. Các chunk liên quan + câu hỏi được đưa vào LLM để sinh câu trả lời, kèm trích dẫn nguồn

**Luồng hoạt động (quiz & chấm điểm):**
1. Từ các chunk đã có, LLM sinh câu hỏi trắc nghiệm (4 đáp án, 1 đúng) và câu hỏi tự luận (kèm đáp án mẫu/key points), gắn với chunk nguồn
2. Câu hỏi được lưu vào question bank (JSON hoặc SQLite)
3. Người dùng chọn phạm vi ôn tập (toàn bộ tài liệu / theo chương) → làm bài trên giao diện Quiz
4. Trắc nghiệm: so sánh đáp án chọn với đáp án đúng — chấm tức thì, không cần gọi LLM
5. Tự luận: gửi câu trả lời của người dùng + đáp án mẫu/key points cho LLM để chấm, trả về điểm số và nhận xét cụ thể (đúng ý nào, thiếu ý nào)

---

## 3. Tech stack (100% miễn phí)

| Thành phần | Công cụ | Ghi chú |
|---|---|---|
| Trích xuất PDF | `pdfplumber` | Mã nguồn mở, free |
| Trích xuất Word | `python-docx` | Mã nguồn mở, free |
| Chia chunk | LangChain `RecursiveCharacterTextSplitter` | Hoặc tự viết để hiểu sâu hơn |
| Embedding | `sentence-transformers` (`all-MiniLM-L6-v2`) | Chạy local, miễn phí tuyệt đối, không giới hạn request |
| Vector DB | Chroma | Local, dễ dùng, free |
| LLM sinh câu trả lời | Gemini 2.5 Flash API | Free tier ~1.500 request/ngày, đủ cho demo |
| Giao diện | Streamlit | Free, code ít, lên UI chat nhanh |
| Sinh câu hỏi (MCQ + tự luận) | Gemini 2.5 Flash API, ép output dạng JSON | Prompt yêu cầu model chỉ dùng nội dung chunk, tránh bịa câu hỏi ngoài tài liệu |
| Question bank | JSON file hoặc SQLite | Lưu câu hỏi kèm đáp án/rubric + chunk nguồn để chấm điểm & trích dẫn |
| Chấm trắc nghiệm | Rule-based (so sánh đáp án) | Không cần LLM, tức thì, 100% nhất quán |
| Chấm tự luận | Gemini 2.5 Flash API (LLM-as-judge) | So câu trả lời user với đáp án mẫu/key points, trả điểm + nhận xét |
| Deploy | Streamlit Community Cloud / HuggingFace Spaces | Free, có link demo public |

> **Lưu ý:** Rate limit/điều khoản free tier của Gemini có thể thay đổi theo thời gian — kiểm tra lại trên Google AI Studio trước khi build để chắc chắn số liệu mới nhất.

---

## 4. Roadmap từng bước

### Bước 1 — Kiểm tra retrieval (chưa cần LLM)
- [ ] Đọc 1 file PDF mẫu
- [ ] Chia chunk văn bản
- [ ] Embed chunk bằng `sentence-transformers`
- [ ] Lưu vào Chroma
- [ ] Thử 1 câu hỏi, in ra chunk liên quan nhất
- **Mục tiêu:** xác nhận bước "tìm đúng đoạn văn bản" hoạt động tốt trước khi thêm LLM

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

### Bước 6 — Sinh câu hỏi ôn tập từ tài liệu
- [ ] Thiết kế prompt sinh câu hỏi với ràng buộc JSON schema (mcq + tự luận), yêu cầu model chỉ dùng nội dung chunk được cung cấp
- [ ] Với mỗi chunk/section, gọi Gemini sinh N câu trắc nghiệm (4 đáp án, 1 đúng) + N câu tự luận (kèm đáp án mẫu/key points)
- [ ] Lưu question bank (JSON hoặc SQLite), gắn mỗi câu hỏi với chunk nguồn để chấm điểm và trích dẫn sau này
- [ ] Cho người dùng chọn phạm vi tạo câu hỏi (toàn bộ tài liệu / theo chương / theo chủ đề)
- **Mục tiêu:** có bộ câu hỏi được sinh tự động, bám sát nội dung tài liệu, không bịa đặt

### Bước 7 — Giao diện làm bài & Tự chấm điểm
- [ ] Thêm tab "Quiz" trong Streamlit, tách biệt với tab "Chat"
- [ ] Hiển thị câu trắc nghiệm (radio button) và câu tự luận (text area)
- [ ] Chấm trắc nghiệm: so sánh đáp án chọn với đáp án đúng — rule-based, hiển thị kết quả tức thì
- [ ] Chấm tự luận: gọi LLM đóng vai giám khảo (LLM-as-judge) — so câu trả lời với đáp án mẫu/key points, trả về điểm số + nhận xét (đã đúng ý nào, thiếu ý nào)
- [ ] Hiển thị kết quả kèm trích dẫn lại đoạn tài liệu liên quan
- **Mục tiêu:** người dùng ôn tập và nhận phản hồi ngay, không cần người chấm thủ công
- **Lưu ý:** LLM chấm tự luận có thể không hoàn toàn nhất quán giữa các lần chấm — nên ghi rõ hạn chế này trong README, đây cũng là điểm thú vị để bàn luận trong phỏng vấn về đánh giá LLM output

### Bước 8 — Cải thiện chất lượng (nâng cao)
- [ ] Semantic chunking thay vì chia cứng theo số ký tự
- [ ] Thêm conversation memory (nhớ ngữ cảnh nhiều lượt hỏi-đáp)
- [ ] Re-ranking: xếp hạng lại độ liên quan sau khi lấy top-k chunk
- [ ] Lưu lịch sử làm bài (SQLite) để theo dõi tiến bộ qua thời gian — thêm góc nhìn "learning progress dashboard"

### Bước 9 — Đánh giá & Deploy
- [ ] Soạn bộ câu hỏi test, đo tỷ lệ trả lời đúng + trích dẫn chính xác
- [ ] (Tùy chọn) Dùng thư viện RAGAS để đánh giá bài bản hơn
- [ ] Deploy lên Streamlit Cloud hoặc HuggingFace Spaces
- [ ] Viết README: vấn đề giải quyết, kiến trúc, demo link, hạn chế

---

## 5. Định hướng nâng cấp sau MVP (không bắt buộc ngay)

Sau khi MVP chạy ổn, cân nhắc chọn 1 domain cụ thể để có câu chuyện rõ ràng hơn thay vì "chatbot chat với PDF" chung chung, ví dụ:
- Trợ lý tra cứu luật/thuế Việt Nam
- Chatbot hỏi đáp tài liệu học tập
- Trợ lý đọc hợp đồng/tài liệu nội bộ

---

## 6. Gợi ý viết cho CV

Ví dụ câu mô tả:
> "Xây dựng AI Study Assistant: RAG chatbot cho phép hỏi-đáp trên tài liệu PDF/docx kèm trích dẫn nguồn, có khả năng tự sinh câu hỏi trắc nghiệm/tự luận từ tài liệu và tự chấm điểm bài làm (rule-based cho trắc nghiệm, LLM-as-judge cho tự luận). Stack: sentence-transformers + Chroma cho retrieval, Gemini API cho sinh nội dung và chấm điểm. Deploy public demo trên Streamlit Cloud."

Nên có con số cụ thể nếu đo được, ví dụ: % câu trả lời đúng trên bộ test, thời gian phản hồi trung bình, số lượng tài liệu/định dạng hỗ trợ, số câu hỏi sinh ra mỗi tài liệu, độ tương quan giữa điểm LLM chấm và điểm người chấm thủ công (nếu đo thử).

---

## 7. Checklist tổng thể

- [ ] Bước 1: Retrieval hoạt động
- [ ] Bước 2: LLM sinh câu trả lời
- [ ] Bước 3: Trích dẫn nguồn
- [ ] Bước 4: Đa file
- [ ] Bước 5: Giao diện Streamlit
- [ ] Bước 6: Sinh câu hỏi ôn tập
- [ ] Bước 7: Giao diện làm bài & tự chấm điểm
- [ ] Bước 8: Cải thiện chất lượng (tùy chọn)
- [ ] Bước 9: Đánh giá & Deploy
- [ ] Viết README + mô tả CV
