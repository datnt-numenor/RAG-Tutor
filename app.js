/**
 * app.js
 * JavaScript logic for RAGTutor Frontend Mockup
 * Handles accessibility, quiz logic, simulated AI grading, citations scroll, and document upload/switch.
 */

document.addEventListener("DOMContentLoaded", () => {
    // State management
    let currentFontSize = 16; // in pixels
    let dyslexiaMode = false;
    let focusMode = false;
    let xpPoints = 350;
    let streakDays = 3;
    let uploadedCount = 1;

    // Elements
    const body = document.body;
    const documentContent = document.getElementById("document-text");
    const chatFeed = document.getElementById("chat-feed");
    const essayInput = document.getElementById("essay-input");
    const btnSubmitEssay = document.getElementById("btn-submit-essay");
    const evaluationCard = document.getElementById("evaluation-card");
    const xpBadgeText = document.querySelector(".xp-badge");
    const streakBadgeText = document.querySelector(".streak-badge");

    // Sidebar elements
    const sidebar = document.getElementById("app-sidebar");
    const sidebarToggle = document.getElementById("sidebar-toggle");
    const toggleIcon = document.getElementById("toggle-icon");
    const uploadZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("file-input");
    const processingStatus = document.getElementById("processing-status");
    const statusFilename = document.getElementById("status-filename");
    const statusPercent = document.getElementById("status-percent");
    const progressFill = document.getElementById("status-progress-fill");
    const fileList = document.getElementById("file-list");
    const fileCount = document.getElementById("file-count");

    // Document dynamic sections
    const docActiveTitle = document.getElementById("doc-active-title");
    const docDynamicBody = document.getElementById("doc-dynamic-body");

    // 1. Sidebar Collapse/Expand Logic
    sidebarToggle.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
        const isCollapsed = sidebar.classList.contains("collapsed");
        
        // Move toggle button and change icon
        sidebarToggle.style.left = isCollapsed ? "0px" : "268px";
        toggleIcon.className = isCollapsed ? "fa-solid fa-chevron-right" : "fa-solid fa-chevron-left";
    });

    // 2. Accessibility handlers
    document.getElementById("btn-dyslexia").addEventListener("click", function() {
        dyslexiaMode = !dyslexiaMode;
        this.classList.toggle("active", dyslexiaMode);
        body.classList.toggle("dyslexia-active", dyslexiaMode);
    });

    document.getElementById("btn-focus").addEventListener("click", function() {
        focusMode = !focusMode;
        this.classList.toggle("active", focusMode);
        documentContent.classList.toggle("focus-active", focusMode);
        
        if (!focusMode) {
            document.querySelectorAll(".focus-target").forEach(el => {
                el.classList.remove("focus-target");
            });
        }
    });

    // Make elements focusable for Focus Mode
    function setupFocusHover() {
        const focusableElements = documentContent.querySelectorAll("p, h1, .quiz-card, .essay-card");
        focusableElements.forEach(el => {
            el.addEventListener("mouseenter", () => {
                if (focusMode) {
                    focusableElements.forEach(item => item.classList.remove("focus-target"));
                    el.classList.add("focus-target");
                }
            });
        });
    }
    setupFocusHover();

    document.getElementById("btn-zoom-in").addEventListener("click", () => {
        if (currentFontSize < 24) {
            currentFontSize += 2;
            documentContent.style.fontSize = `${currentFontSize}px`;
        }
    });

    document.getElementById("btn-zoom-out").addEventListener("click", () => {
        if (currentFontSize > 12) {
            currentFontSize -= 2;
            documentContent.style.fontSize = `${currentFontSize}px`;
        }
    });

    // 3. Document Content Templates
    const documentTemplates = {
        "default-rag": {
            title: "Chương 2: Kiến trúc ứng dụng Retrieval-Augmented Generation (RAG)",
            html: `
                <p>Mô hình ngôn ngữ lớn (LLM) tuy mạnh mẽ nhưng thường mắc phải hạn chế nghiêm trọng về tính cập nhật và hiện tượng "bịa đặt" thông tin (hallucination). Để giải quyết vấn đề này, kiến trúc <span class="highlight highlight-yellow" id="ref-rag" title="Định nghĩa RAG">Retrieval-Augmented Generation (RAG)</span> đã được ra đời như một phương pháp tối ưu giúp bổ sung tri thức ngoài cho mô hình mà không cần tinh chỉnh (fine-tuning).</p>

                <p>Quy trình hoạt động của RAG gồm hai bước chính: truy xuất (Retrieval) và tạo sinh (Generation). Trong giai đoạn truy xuất, câu hỏi của người dùng được chuyển đổi thành vector embedding. Sau đó, hệ thống tìm kiếm trong cơ sở dữ liệu vector để trích xuất các đoạn văn bản (chunks) có mức độ tương đồng ngữ nghĩa cao nhất.</p>

                <p>Việc <span class="highlight highlight-green" id="ref-vectordb" title="Vai trò Vector DB">sử dụng cơ sở dữ liệu vector (như Chroma DB, Pinecone)</span> đóng vai trò then chốt trong việc tăng tốc độ và độ chính xác của quá trình tìm kiếm ngữ nghĩa, đảm bảo các context được đưa vào prompt của LLM là phù hợp nhất.</p>

                <!-- Câu hỏi trắc nghiệm Inline -->
                <div class="quiz-card inline-quiz">
                    <div class="quiz-header">
                        <span class="quiz-tag"><i class="fa-solid fa-circle-question"></i> Câu hỏi trắc nghiệm</span>
                        <span class="quiz-xp">+10 XP</span>
                    </div>
                    <p class="quiz-question">Thành phần nào chịu trách nhiệm lưu trữ các vector biểu diễn và tính toán độ tương đồng ngữ nghĩa trong kiến trúc RAG?</p>
                    <div class="quiz-options">
                        <div class="option-card" data-correct="false">
                            <span class="option-letter">A</span>
                            <span class="option-text">SQLite / Hệ quản trị CSDL quan hệ</span>
                        </div>
                        <div class="option-card" data-correct="true">
                            <span class="option-letter">B</span>
                            <span class="option-text">Chroma Vector DB / Cơ sở dữ liệu Vector</span>
                        </div>
                        <div class="option-card" data-correct="false">
                            <span class="option-letter">C</span>
                            <span class="option-text">Thư viện python-docx trích xuất text</span>
                        </div>
                        <div class="option-card" data-correct="false">
                            <span class="option-letter">D</span>
                            <span class="option-text">Gemini 2.5 Flash API</span>
                        </div>
                    </div>
                    <div class="quiz-feedback hidden">
                        <div class="feedback-icon"></div>
                        <div class="feedback-text"></div>
                    </div>
                </div>

                <p>Tuy nhiên, RAG vẫn có thể gặp phải một số lỗi nghiêm trọng. Điển hình là khi tài liệu đầu vào bị thiếu thông tin hoặc khi <span class="highlight highlight-orange" id="ref-hallucination" title="Lỗi Hallucination trong RAG">LLM bỏ qua ngữ cảnh được cung cấp và tự tạo câu trả lời theo dữ liệu huấn luyện cũ</span>. Đây gọi là hiện tượng hallucination trong RAG, yêu cầu việc thiết lập các bộ kiểm chuẩn và chấm điểm chặt chẽ.</p>

                <!-- Câu hỏi tự luận ôn tập -->
                <div class="essay-card">
                    <div class="quiz-header">
                        <span class="quiz-tag"><i class="fa-solid fa-pen-clip"></i> Bài tập tự luận</span>
                        <span class="quiz-xp">+50 XP</span>
                    </div>
                    <p class="quiz-question">Hãy giải thích sự khác biệt giữa kiến trúc RAG và mô hình LLM truyền thống trong việc giảm thiểu hiện tượng "bịa đặt" thông tin (hallucination).</p>
                    <textarea id="essay-input" placeholder="Nhập câu trả lời tự luận của bạn tại đây (tối thiểu 20 từ để AI đánh giá hiệu quả nhất)..."></textarea>
                    <div class="essay-actions">
                        <button id="btn-submit-essay" class="btn-primary">
                            <i class="fa-solid fa-paper-plane"></i> Nộp bài tự luận
                        </button>
                    </div>
                </div>
            `,
            tutorWelcome: "Gâu! Đã mở tài liệu **Kiến trúc RAG**. Mình đã chuẩn bị sẵn bộ câu hỏi ôn tập tương ứng ở bên trái, hãy thử giải đáp xem sao nha! 🐾",
            citationbadges: `
                <span class="citation-badge" data-target="ref-vectordb">
                    <i class="fa-solid fa-bookmark"></i> Xem nguồn: Vai trò Vector DB
                </span>
                <span class="citation-badge" data-target="ref-hallucination">
                    <i class="fa-solid fa-bookmark"></i> Xem nguồn: Lỗi Hallucination
                </span>
            `
        },
        "neural-network": {
            title: "Tổng quan về Mạng Neural Nhân tạo (Artificial Neural Network - ANN)",
            html: `
                <p>Mạng Neural Nhân tạo (ANN) là mô hình toán học - tính toán được thiết kế dựa trên cấu trúc sinh học của bộ não con người. Khái niệm cốt lõi của ANN là <span class="highlight highlight-yellow" id="ref-ann" title="Định nghĩa ANN">mô phỏng lại cách thức các tế bào thần kinh truyền tín hiệu thông qua liên kết sinh học</span>.</p>

                <p>Mạng neural cấu tạo gồm các lớp nút: lớp đầu vào (Input layer), một hoặc nhiều lớp ẩn (Hidden layers), và lớp đầu ra (Output layer). Mỗi liên kết giữa hai neuron chứa một trọng số (weight) thể hiện mức độ mạnh yếu của liên kết.</p>

                <p>Trong quá trình huấn luyện, thuật toán sẽ tự động điều chỉnh các trọng số này. <span class="highlight highlight-green" id="ref-backprop" title="Cơ chế Lan truyền ngược">Thuật toán Lan truyền ngược (Backpropagation)</span> là công cụ chủ chốt giúp tính toán độ lỗi ngược từ đầu ra để cập nhật lại các trọng số, tối ưu hóa độ chính xác của mô hình.</p>

                <!-- Câu hỏi trắc nghiệm Neural Network -->
                <div class="quiz-card inline-quiz">
                    <div class="quiz-header">
                        <span class="quiz-tag"><i class="fa-solid fa-circle-question"></i> Câu hỏi trắc nghiệm</span>
                        <span class="quiz-xp">+10 XP</span>
                    </div>
                    <p class="quiz-question">Thuật toán nào được sử dụng để lan truyền gradient sai số từ đầu ra ngược về đầu vào để tối ưu hóa trọng số của mạng?</p>
                    <div class="quiz-options">
                        <div class="option-card" data-correct="false">
                            <span class="option-letter">A</span>
                            <span class="option-text">Gradient Descent đơn thuần / Xuống dốc</span>
                        </div>
                        <div class="option-card" data-correct="true">
                            <span class="option-letter">B</span>
                            <span class="option-text">Backpropagation / Lan truyền ngược</span>
                        </div>
                        <div class="option-card" data-correct="false">
                            <span class="option-letter">C</span>
                            <span class="option-text">Feedforward / Truyền xuôi dữ liệu</span>
                        </div>
                        <div class="option-card" data-correct="false">
                            <span class="option-letter">D</span>
                            <span class="option-text">CSDL Vector Chroma</span>
                        </div>
                    </div>
                    <div class="quiz-feedback hidden">
                        <div class="feedback-icon"></div>
                        <div class="feedback-text"></div>
                    </div>
                </div>

                <p>Một tham số quan trọng trong quá trình huấn luyện là hàm kích hoạt (Activation Function). Nhờ có hàm kích hoạt, mô hình mạng neural mới học được các mối liên hệ phi tuyến phức tạp trong dữ liệu. Nếu không có hàm kích hoạt, <span class="highlight highlight-orange" id="ref-activation" title="Hàm kích hoạt phi tuyến">mạng neural sẽ chỉ tương đương một mô hình hồi quy tuyến tính đơn giản</span> bất kể nó có bao nhiêu lớp ẩn.</p>

                <!-- Câu hỏi tự luận Neural Network -->
                <div class="essay-card">
                    <div class="quiz-header">
                        <span class="quiz-tag"><i class="fa-solid fa-pen-clip"></i> Bài tập tự luận</span>
                        <span class="quiz-xp">+50 XP</span>
                    </div>
                    <p class="quiz-question">Hãy trình bày ngắn gọn vai trò của Hàm kích hoạt (Activation Function) trong Mạng Neural Nhân tạo.</p>
                    <textarea id="essay-input" placeholder="Nhập câu trả lời tự luận của bạn tại đây (tối thiểu 20 từ để AI đánh giá hiệu quả nhất)..."></textarea>
                    <div class="essay-actions">
                        <button id="btn-submit-essay" class="btn-primary">
                            <i class="fa-solid fa-paper-plane"></i> Nộp bài tự luận
                        </button>
                    </div>
                </div>
            `,
            tutorWelcome: "Gâu! Đã mở tài liệu **Mạng Neural Nhân tạo**. Hãy thử trả lời câu hỏi trắc nghiệm và tự luận để củng cố về trọng số và lan truyền ngược nhé! 🐾",
            citationbadges: `
                <span class="citation-badge" data-target="ref-backprop">
                    <i class="fa-solid fa-bookmark"></i> Xem nguồn: Lan truyền ngược
                </span>
                <span class="citation-badge" data-target="ref-activation">
                    <i class="fa-solid fa-bookmark"></i> Xem nguồn: Hàm kích hoạt
                </span>
            `
        }
    };

    // 4. File Upload Drag & Drop simulation logic
    uploadZone.addEventListener("click", () => {
        fileInput.click();
    });

    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("dragover");
    });

    uploadZone.addEventListener("dragleave", () => {
        uploadZone.classList.remove("dragover");
    });

    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleUploadedFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (fileInput.files.length > 0) {
            handleUploadedFile(fileInput.files[0]);
        }
    });

    function handleUploadedFile(file) {
        // Toggle processing animation
        processingStatus.classList.remove("hidden");
        statusFilename.innerText = file.name;
        
        let progress = 0;
        progressFill.style.width = "0%";
        statusPercent.innerText = "0%";

        const interval = setInterval(() => {
            progress += 10;
            progressFill.style.width = `${progress}%`;
            statusPercent.innerText = `${progress}%`;

            if (progress >= 100) {
                clearInterval(interval);
                
                // Hide loader and add file to list
                processingStatus.classList.add("hidden");
                
                const fileId = file.name.toLowerCase().includes("neural") || file.name.toLowerCase().includes("mang") ? "neural-network" : "default-rag";
                const isPdf = file.name.endsWith(".pdf");
                const isDocx = file.name.endsWith(".docx");
                
                let iconClass = "fa-solid fa-file-lines txt";
                if (isPdf) iconClass = "fa-solid fa-file-pdf pdf";
                else if (isDocx) iconClass = "fa-solid fa-file-word docx";

                const newLi = document.createElement("li");
                newLi.className = "file-item";
                newLi.setAttribute("data-file-id", fileId);
                newLi.innerHTML = `
                    <i class="${iconClass} file-icon"></i>
                    <span class="file-name" title="${file.name}">${file.name}</span>
                    <i class="fa-solid fa-circle-check success-icon"></i>
                `;

                fileList.appendChild(newLi);
                uploadedCount++;
                fileCount.innerText = uploadedCount;

                // Add click listener to the new file item
                setupFileClickEvent(newLi);

                // Shiba chat feedback
                appendChatBubble("ai", `🐾 Gâu! Đã nạp và xử lý tài liệu <strong>${file.name}</strong> thành công! Mình đã chia thành các mảnh (chunks), chạy embedding và lưu vào CSDL Vector Chroma DB rồi. Hãy click chọn file này trong danh sách để bắt đầu học tập nhé!`);
            }
        }, 150);
    }

    // 5. Switch document logic
    function setupFileClickEvent(item) {
        item.addEventListener("click", () => {
            // Remove active classes
            document.querySelectorAll(".file-item").forEach(el => el.classList.remove("active"));
            item.classList.add("active");

            const fileId = item.getAttribute("data-file-id");
            const template = documentTemplates[fileId] || documentTemplates["default-rag"];

            // Swap text contents
            docActiveTitle.innerText = template.title;
            docDynamicBody.innerHTML = template.html;

            // Reset evaluation box
            evaluationCard.classList.add("hidden");

            // Update citations indicators inside tutor box
            document.getElementById("citation-container").innerHTML = template.citationbadges;

            // Post tutor greeting
            appendChatBubble("ai", template.tutorWelcome);

            // Re-setup all events on new elements
            setupQuizEvents();
            setupEssaySubmitEvent();
            setupCitationEvents();
            setupFocusHover();
        });
    }

    // Register click for default file items
    document.querySelectorAll(".file-item").forEach(item => {
        setupFileClickEvent(item);
    });

    // 6. Inline quiz events register
    function setupQuizEvents() {
        const optionCards = documentContent.querySelectorAll(".option-card");
        const quizFeedback = documentContent.querySelector(".quiz-feedback");
        let quizCompleted = false;

        optionCards.forEach(card => {
            card.addEventListener("click", () => {
                if (quizCompleted) return;

                const isCorrect = card.getAttribute("data-correct") === "true";
                
                if (isCorrect) {
                    card.classList.add("correct");
                    quizCompleted = true;
                    
                    quizFeedback.className = "quiz-feedback success";
                    quizFeedback.querySelector(".feedback-icon").innerHTML = '<i class="fa-solid fa-circle-check fa-lg"></i>';
                    quizFeedback.querySelector(".feedback-text").innerHTML = 
                        "<strong>Chính xác!</strong> Câu trả lời rất chính xác, bạn được cộng 10 XP ôn luyện.";
                    
                    updateXP(10);
                    appendChatBubble("ai", "🐾 Gâu! Quá giỏi! Câu trả lời trắc nghiệm hoàn toàn chính xác. Bạn cộng thêm 10 XP nhé.");
                } else {
                    card.classList.add("incorrect");
                    
                    quizFeedback.className = "quiz-feedback error";
                    quizFeedback.querySelector(".feedback-icon").innerHTML = '<i class="fa-solid fa-circle-xmark fa-lg"></i>';
                    quizFeedback.querySelector(".feedback-text").innerHTML = 
                        "<strong>Hừm, chưa chính xác.</strong> Bạn hãy đọc kỹ đoạn văn bản được highlight màu xanh lá ở phía trên và thử lại nhé.";
                    
                    appendChatBubble("ai", "Gâu... Câu trắc nghiệm này chưa đúng rồi. Hãy đọc kỹ phần highlight màu xanh lá và thử lại xem sao.");
                    
                    setTimeout(() => {
                        card.classList.remove("incorrect");
                    }, 2000);
                }
                
                quizFeedback.classList.remove("hidden");
            });
        });
    }
    setupQuizEvents();

    // 7. Essay submits event register
    function setupEssaySubmitEvent() {
        const essayInputEl = document.getElementById("essay-input");
        const btnSubmit = document.getElementById("btn-submit-essay");

        if (!btnSubmit) return;

        btnSubmit.addEventListener("click", () => {
            const text = essayInputEl.value.trim();
            
            if (text.length < 20) {
                alert("Câu trả lời hơi ngắn nè! Bạn vui lòng viết chi tiết hơn một chút (tối thiểu 20 ký tự) để chú chó Sparky chấm điểm chính xác nhé! 🐾");
                return;
            }

            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Chú chó Sparky đang chấm bài...';
            essayInputEl.disabled = true;

            setTimeout(() => {
                const textLower = text.toLowerCase();
                let score = 60;
                let summary = "";
                let strengths = [];
                let gaps = [];
                let recommendation = "";

                // Checking inputs
                const isRagDoc = docActiveTitle.innerText.includes("RAG");

                if (isRagDoc) {
                    const hasVector = textLower.includes("vector") || textLower.includes("chroma") || textLower.includes("cơ sở dữ liệu");
                    const hasContext = textLower.includes("context") || textLower.includes("ngữ cảnh") || textLower.includes("tài liệu");
                    const hasHallucination = textLower.includes("hallucination") || textLower.includes("bịa đặt") || textLower.includes("chính xác");

                    if (hasVector && hasContext && hasHallucination) {
                        score = 95;
                        summary = "Xuất sắc! Câu trả lời của bạn cực kỳ toàn diện, làm nổi bật được cả vai trò của cơ sở dữ liệu vector lẫn cơ chế giảm thiểu hallucination bằng context bên ngoài.";
                        strengths = [
                            "Giải thích rõ ràng cơ chế lấy context ngoài giúp LLM không bị giới hạn trong dữ liệu huấn luyện tĩnh.",
                            "Nhấn mạnh vai trò cốt lõi của CSDL Vector trong việc truy xuất dữ liệu ngữ nghĩa.",
                            "Sử dụng thuật ngữ kỹ thuật chính xác và phân tích mạch lạc."
                        ];
                        gaps = ["Hầu như không có thiếu sót lớn nào. Bạn đã nắm rất vững kiến thức phần này!"];
                        recommendation = "Bạn đã hoàn thành xuất sắc bài tập tự luận này. Hãy tiếp tục chuyển sang chương tiếp theo để nghiên cứu về các kỹ thuật Semantic Chunking nâng cao nhé!";
                    } else if (hasContext && hasHallucination) {
                        score = 80;
                        summary = "Tốt lắm! Bạn đã làm rõ được cốt lõi của RAG là đưa context ngoài vào prompt để giảm hallucination so với LLM truyền thống.";
                        strengths = [
                            "Giải thích chính xác cơ chế đưa tài liệu ngoài làm context cho prompt của LLM.",
                            "Nêu rõ sự khác biệt của RAG so với việc LLM tự sinh câu trả lời theo trí nhớ cũ."
                        ];
                        gaps = [
                            "Chưa phân tích sâu về **Cơ sở dữ liệu Vector** - thành phần giúp tìm kiếm các context liên quan nhất từ kho dữ liệu lớn."
                        ];
                        recommendation = "Hãy đọc thêm phần văn bản được highlight màu xanh lá ở cột bên trái để hiểu cách vector DB tăng tốc độ tìm kiếm ngữ nghĩa, và bổ sung ý này vào bài làm nhé.";
                    } else {
                        score = 65;
                        summary = "Đã hoàn thành! Bạn đã nêu được sự khác biệt cơ bản nhưng câu trả lời còn khá chung chung, chưa đi vào kỹ thuật cụ thể của RAG.";
                        strengths = [
                            "Nêu được việc RAG giúp LLM trả lời chính xác hơn."
                        ];
                        gaps = [
                            "Chưa giải thích cơ chế truy xuất (Retrieval) dựa trên Vector Embedding.",
                            "Chưa làm nổi bật được cơ chế hoạt động của Context hỗ trợ prompt để giảm thiểu Hallucination."
                        ];
                        recommendation = "Bạn nên đọc lại toàn bộ bài đọc bên trái, đặc biệt là hai đoạn được highlight màu vàng và xanh lá, để nắm được luồng hoạt động chính của RAG.";
                    }
                } else {
                    // Neural network doc grading logic
                    const hasAnn = textLower.includes("activation") || textLower.includes("kích hoạt") || textLower.includes("phi tuyến");
                    const hasBackprop = textLower.includes("lan truyền") || textLower.includes("backprop") || textLower.includes("trọng số");

                    if (hasAnn && hasBackprop) {
                        score = 90;
                        summary = "Tốt lắm! Bạn giải thích chuẩn xác vai trò tạo tính phi tuyến của hàm kích hoạt và thuật toán lan truyền ngược giúp tối ưu trọng số.";
                        strengths = [
                            "Làm rõ vai trò bắt buộc của hàm kích hoạt giúp học các hàm phi tuyến phức tạp.",
                            "Giải thích đúng sự bổ trợ của thuật toán backpropagation trong việc cập nhật trọng số."
                        ];
                        gaps = ["Có thể làm rõ thêm ví dụ một số hàm kích hoạt phổ biến như ReLU hoặc Sigmoid."];
                        recommendation = "Hãy tham khảo phần lý thuyết và bổ sung thêm ví dụ cụ thể của các hàm kích hoạt để đạt điểm tối đa nha gâu!";
                    } else {
                        score = 70;
                        summary = "Bạn đã có ý thức trả lời nhưng nội dung còn hơi sơ sài, chưa chỉ ra tính chất phi tuyến tối quan trọng của hàm kích hoạt.";
                        strengths = ["Nêu được hàm kích hoạt dùng để tính toán ở các neuron ẩn."];
                        gaps = ["Chưa chỉ ra được nếu thiếu hàm kích hoạt, mạng neural sâu cũng chỉ là hồi quy tuyến tính."];
                        recommendation = "Hãy đọc phần lý thuyết được highlight màu cam ở cột bên trái để bổ sung ý nghĩa của hàm kích hoạt và nộp lại.";
                    }
                }

                // Update evaluation UI
                document.getElementById("eval-score").innerText = `${score}%`;
                document.getElementById("eval-summary").innerText = summary;
                
                const strengthsUl = document.getElementById("list-strengths");
                strengthsUl.innerHTML = "";
                strengths.forEach(str => {
                    const li = document.createElement("li");
                    li.innerText = str;
                    strengthsUl.appendChild(li);
                });

                const gapsUl = document.getElementById("list-gaps");
                gapsUl.innerHTML = "";
                gaps.forEach(gap => {
                    const li = document.createElement("li");
                    li.innerText = gap;
                    gapsUl.appendChild(li);
                });

                document.getElementById("eval-recommendation").innerText = recommendation;

                btnSubmit.innerHTML = '<i class="fa-solid fa-check-double"></i> Đã nộp & AI đã chấm';
                
                evaluationCard.classList.remove("hidden");
                evaluationCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

                appendChatBubble("ai", `Gâu gâu! Sparky đã chấm điểm bài tự luận của bạn xong rồi nhé. Bạn đạt <strong>${score}% điểm</strong>! Hãy xem chi tiết bảng đánh giá ưu/nhược điểm mình vừa gửi phía dưới nha.🐾`);

                updateXP(50);
            }, 1500);
        });
    }
    setupEssaySubmitEvent();

    // 8. Citations events register
    function setupCitationEvents() {
        document.querySelectorAll(".citation-badge").forEach(badge => {
            badge.addEventListener("click", () => {
                const targetId = badge.getAttribute("data-target");
                const targetEl = document.getElementById(targetId);

                if (targetEl) {
                    if (focusMode) {
                        document.querySelectorAll(".focus-target").forEach(el => el.classList.remove("focus-target"));
                        targetEl.closest("p").classList.add("focus-target");
                    }

                    targetEl.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });

                    targetEl.classList.add("citation-highlight-active");
                    
                    appendChatBubble("ai", `Gâu! Đã cuộn đến đoạn tài liệu nguồn liên quan ở cột bên trái: "<strong>${targetEl.getAttribute("title")}</strong>".`);

                    setTimeout(() => {
                        targetEl.classList.remove("citation-highlight-active");
                    }, 3000);
                }
            });
        });
    }
    setupCitationEvents();

    // 9. Highlights tip bubble click trigger
    document.querySelectorAll(".highlight").forEach(hl => {
        hl.addEventListener("click", () => {
            const id = hl.id;
            let desc = "";

            if (id === "ref-rag") {
                desc = "💡 <strong>RAG (Retrieval-Augmented Generation):</strong> Giống như việc cho phép học sinh mang sách vào phòng thi. Thay vì bắt LLM nhớ tất cả mọi thứ, RAG sẽ tìm các tài liệu phù hợp bên ngoài rồi đưa vào đề thi để LLM làm bài chính xác hơn.";
            } else if (id === "ref-vectordb") {
                desc = "💡 <strong>CSDL Vector:</strong> Khác với CSDL SQL tìm kiếm từ khóa khớp 100%, CSDL Vector tính toán 'khoảng cách' nghĩa của từ. Ví dụ: từ 'mèo' và 'cat' hay 'thú cưng' có khoảng cách rất gần nhau trong không gian vector.";
            } else if (id === "ref-hallucination") {
                desc = "💡 <strong>Hallucination (Bịa đặt):</strong> Do mô hình LLM bản chất là dự đoán từ tiếp theo có xác suất cao nhất, nên nếu không có tài liệu kiểm chứng (context) đáng tin cậy, nó sẽ tự bịa ra các thông tin nghe rất hợp lý nhưng hoàn toàn sai sự thật.";
            } else if (id === "ref-ann") {
                desc = "💡 <strong>ANN (Mạng Neural Nhân tạo):</strong> Mô hình học máy mô phỏng cấu trúc neuron não bộ, dùng trọng số kết nối để học và nhận dạng quy luật dữ liệu lớn.";
            } else if (id === "ref-backprop") {
                desc = "💡 <strong>Lan truyền ngược:</strong> Thuật toán đẩy sai số từ đầu ra ngược về các lớp ẩn để cập nhật trọng số, làm giảm sai số tổng thể của mô hình huấn luyện.";
            } else if (id === "ref-activation") {
                desc = "💡 <strong>Hàm kích hoạt:</strong> Thêm các phép toán phi tuyến (như ReLU, Sigmoid). Thiếu nó, mạng neural nhiều lớp cũng chỉ tính toán được các hàm tuyến tính thẳng tắp đơn điệu.";
            }

            appendChatBubble("ai", desc);
        });
    });

    // Helper functions
    function appendChatBubble(sender, text) {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${sender}-bubble`;
        
        const content = document.createElement("p");
        content.innerHTML = text;
        
        const time = document.createElement("span");
        time.className = "chat-time";
        time.innerText = "Vừa xong";
        
        bubble.appendChild(content);
        bubble.appendChild(time);
        
        chatFeed.appendChild(bubble);
        chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    function updateXP(amount) {
        xpPoints += amount;
        xpBadgeText.innerHTML = `<i class="fa-solid fa-star"></i> ${xpPoints} XP`;
        
        xpBadgeText.style.transform = "scale(1.1)";
        setTimeout(() => {
            xpBadgeText.style.transform = "scale(1)";
        }, 150);
    }
});
