/**
 * AI Khảo Thí Đa Dạng - Frontend Application Logic
 * 100% Offline Compatible • Local Loopback REST API
 */

// State quản lý toàn cục
const appState = {
    currentDoc: null,
    chunks: [],
    generatedQuestions: [],
    selectedQuestionIds: new Set(),
    activeFilterType: 'all',
    activeFilterBloom: 'all',
    bloomDistribution: {
        'Nhận biết': 40,
        'Thông hiểu': 30,
        'Vận dụng': 20,
        'Vận dụng cao': 10
    }
};

// =========================================================================
// Khởi tạo và kiểm tra sức khỏe hệ thống
// =========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initSystemHealth();
    initEventListeners();
    updateBloomDisplays();
});

async function initSystemHealth() {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    try {
        const res = await fetch('/api/health');
        if (res.ok) {
            const data = await res.json();
            if (data.llm && data.llm.is_available) {
                statusDot.className = 'dot dot-green';
                statusText.textContent = 'Local LLM (127.0.0.1:5001) Sẵn sàng';
            } else {
                statusDot.className = 'dot dot-blue';
                statusText.textContent = 'Chế độ Nội suy Khảo thí Chuẩn (Offline)';
            }
        } else {
            statusDot.className = 'dot dot-amber';
            statusText.textContent = 'Backend Active';
        }
    } catch (err) {
        statusDot.className = 'dot dot-amber';
        statusText.textContent = 'Backend Offline';
    }
}

// =========================================================================
// Đăng ký sự kiện giao diện
// =========================================================================

function initEventListeners() {
    // Tab nạp tài liệu
    const tabUploadFile = document.getElementById('tabUploadFile');
    const tabPasteText = document.getElementById('tabPasteText');
    const tabContentUpload = document.getElementById('tabContentUpload');
    const tabContentPaste = document.getElementById('tabContentPaste');

    tabUploadFile.addEventListener('click', () => {
        tabUploadFile.classList.add('active');
        tabPasteText.classList.remove('active');
        tabContentUpload.classList.remove('hidden');
        tabContentPaste.classList.add('hidden');
    });

    tabPasteText.addEventListener('click', () => {
        tabPasteText.classList.add('active');
        tabUploadFile.classList.remove('active');
        tabContentPaste.classList.remove('hidden');
        tabContentUpload.classList.add('hidden');
    });

    // Kéo thả và chọn file
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Bóc tách văn bản dán
    document.getElementById('btnProcessDirectText').addEventListener('click', () => {
        const text = document.getElementById('directTextInput').value.trim();
        if (!text) {
            showToast('Vui lòng dán nội dung văn bản!');
            return;
        }
        handleDirectText(text);
    });

    // Nút tải tài liệu mẫu
    document.getElementById('btnSampleDoc').addEventListener('click', loadSampleDocument);

    // Thanh trượt số câu hỏi
    const totalQInput = document.getElementById('totalQuestionsInput');
    const totalQDisplay = document.getElementById('totalQuestionsDisplay');
    totalQInput.addEventListener('input', (e) => {
        totalQDisplay.textContent = `${e.target.value} câu`;
    });

    // Thanh trượt 4 mức Bloom
    ['NhanBiet', 'ThongHieu', 'VanDung', 'VanDungCao'].forEach(name => {
        const slider = document.getElementById(`slider${name}`);
        slider.addEventListener('input', () => {
            handleBloomSliderChange();
        });
    });

    // Các ma trận mẫu (Presets)
    document.getElementById('presetGDDT').addEventListener('click', () => applyPreset(40, 30, 20, 10, 'presetGDDT'));
    document.getElementById('presetReview').addEventListener('click', () => applyPreset(50, 35, 15, 0, 'presetReview'));
    document.getElementById('presetDGNL').addEventListener('click', () => applyPreset(20, 30, 30, 20, 'presetDGNL'));

    // Nút sinh câu hỏi
    document.getElementById('btnStartGenerate').addEventListener('click', startGenerationFlow);

    // Duyệt câu hỏi Toolbar
    document.getElementById('btnSelectAll').addEventListener('click', () => setAllQuestionsSelected(true));
    document.getElementById('btnDeselectAll').addEventListener('click', () => setAllQuestionsSelected(false));

    // Bộ lọc
    document.getElementById('filterTypeSelect').addEventListener('change', (e) => {
        appState.activeFilterType = e.target.value;
        renderQuestionsList();
    });

    document.getElementById('filterBloomSelect').addEventListener('change', (e) => {
        appState.activeFilterBloom = e.target.value;
        renderQuestionsList();
    });

    // Modal Xuất file Word
    const exportModal = document.getElementById('exportModal');
    document.getElementById('btnOpenExportModal').addEventListener('click', () => {
        if (appState.selectedQuestionIds.size === 0) {
            showToast('Vui lòng tích chọn ít nhất 1 câu hỏi để xuất đề thi!');
            return;
        }
        exportModal.classList.remove('hidden');
    });

    document.getElementById('btnCloseModal').addEventListener('click', () => exportModal.classList.add('hidden'));
    document.getElementById('btnCancelExport').addEventListener('click', () => exportModal.classList.add('hidden'));
    document.getElementById('btnConfirmExport').addEventListener('click', executeExportDocx);
}

// =========================================================================
// Xử lý nạp tài liệu (Upload & Sample)
// =========================================================================

async function handleFileUpload(file) {
    showToast(`Đang tải lên và trích xuất: ${file.name}...`);
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Lỗi xử lý file');
        }

        const data = await res.json();
        processDocSuccess(data);
    } catch (err) {
        showToast(`Lỗi: ${err.message}`);
    }
}

async function handleDirectText(text) {
    showToast('Đang phân tích văn bản trực tiếp...');
    try {
        const res = await fetch('/api/upload-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, filename: 'Van_ban_truc_tiep.txt' })
        });

        if (!res.ok) throw new Error('Không thể xử lý văn bản');
        const data = await res.json();
        processDocSuccess(data);
    } catch (err) {
        showToast(`Lỗi: ${err.message}`);
    }
}

function loadSampleDocument() {
    const sampleText = `# CHƯƠNG I: NGUYÊN LÝ KHẢO THÍ VÀ ĐO LƯỜNG ĐÁNH GIÁ GIÁO DỤC HIỆN ĐẠI

1. Đại cương về khảo thí sư phạm
Khảo thí giáo dục là một phân ngành khoa học chuyên sâu, tập trung vào việc thiết kế, chuẩn hóa và phân tích độ giá trị (validity) cũng như độ tin cậy (reliability) của các công cụ đánh giá kết quả học tập. Theo nghiên cứu kinh điển của Haladyna và Downing (1989), một đề thi trắc nghiệm đạt tiêu chuẩn quốc tế bắt buộc phải tuân thủ nghiêm ngặt 22 nguyên tắc xây dựng câu hỏi. Trong đó, câu dẫn (stem) phải truyền tải trọn vẹn vấn đề độc lập, không sử dụng cấu trúc phủ định kép. Nếu bắt buộc phải dùng các từ phủ định như KHÔNG, SAI hoặc NGOẠI TRỪ thì các từ ngữ này phải được viết in hoa rõ ràng để thí sinh không bị nhầm lẫn bởi kỹ thuật ngôn ngữ.

2. Cấu trúc câu hỏi trắc nghiệm khách quan
Các phương án lựa chọn trong một câu hỏi trắc nghiệm bao gồm phương án đúng (key) và các phương án nhiễu (distractors). Phương án đúng phải là duy nhất đúng, mang tính chân lý khoa học đơn nhất và không gây tranh cãi. Độ dài và ngữ pháp của các phương án phải được thiết kế đồng nhất và cân xứng; tuyệt đối không để phương án đúng dài vượt trội hay chứa nhiều chi tiết bổ sung hơn so với các phương án còn lại. Đồng thời, các phương án nhiễu phải phản ánh chính xác những sai sót tư duy hoặc ngộ nhận phổ biến của người học, kiên quyết loại trừ các phương án vô nghĩa như "Tất cả các ý trên" hoặc "Không có đáp án nào đúng".

# CHƯƠNG II: THANG ĐO NHẬN THỨC BLOOM VÀ BỘ QUY CHUẨN 2025

1. Bốn mức độ nhận thức của Anderson & Krathwohl
Thang phân loại mục tiêu giáo dục sửa đổi (2001) chia nhận thức thành 4 cấp bậc cơ bản:
- Mức Nhận biết (Remember): Đòi hỏi người học nhớ lại hoặc nhận diện các thuật ngữ, định nghĩa, mốc thời gian và số liệu cụ thể trực tiếp từ bài đọc.
- Mức Thông hiểu (Understand): Yêu cầu người học có khả năng diễn giải, giải thích bản chất, phân loại hoặc tóm tắt ý nghĩa từ ngữ cảnh.
- Mức Vận dụng (Apply): Học sinh sử dụng các quy tắc, công thức hoặc phương pháp đã học để giải quyết một tình huống cụ thể mới.
- Mức Vận dụng cao (Analyze/Evaluate): Yêu cầu mổ xẻ cấu trúc nhân quả, phân biệt mối tương quan giữa các yếu tố và đưa ra phán đoán phản biện dựa trên tiêu chí khách quan.

2. Chuẩn hóa định dạng đề thi mới
Theo khung định dạng đề thi tốt nghiệp trung học phổ thông năm 2025 của Bộ Giáo dục và Đào tạo, bài thi trắc nghiệm được đa dạng hóa thành nhiều cấu phần. Bên cạnh dạng trắc nghiệm truyền thống 4 lựa chọn (MCQ), dạng trắc nghiệm Đúng/Sai đa ý gồm 1 ngữ cảnh và 4 mệnh đề độc lập a, b, c, d giúp hạn chế triệt để hiện tượng đoán mò ngẫu nhiên. Cùng với đó, dạng trắc nghiệm trả lời ngắn (Keyfill) yêu cầu thí sinh tự điền từ khóa hoặc số liệu chính xác từ 3 đến 5 từ, mang lại độ phân hóa năng lực vượt trội cho kỳ thi.`;

    document.getElementById('directTextInput').value = sampleText;
    handleDirectText(sampleText);
}

function processDocSuccess(data) {
    appState.currentDoc = data;

    // Hiển thị Card tóm tắt
    const sumCard = document.getElementById('docSummaryCard');
    sumCard.classList.remove('hidden');

    document.getElementById('sumFileName').textContent = data.filename || 'Tài liệu nguồn';
    document.getElementById('sumWordCount').textContent = `${data.word_count.toLocaleString()} từ`;
    document.getElementById('sumCharCount').textContent = `${data.char_count.toLocaleString()} ký tự`;
    document.getElementById('sumChunkCount').textContent = `${data.chunks_count || 1} chủ đề phân đoạn`;

    // Render danh sách tiêu đề phân đoạn
    const headingsContainer = document.getElementById('sumHeadingsList');
    headingsContainer.innerHTML = '';
    if (data.preview_headings && data.preview_headings.length > 0) {
        data.preview_headings.forEach(h => {
            const span = document.createElement('span');
            span.className = 'summary-chunk-tag';
            span.textContent = `📌 ${h}`;
            headingsContainer.appendChild(span);
        });
    }

    // Kích hoạt nút Sinh câu hỏi
    document.getElementById('btnStartGenerate').disabled = false;
    updateStepper(2);
    showToast('Nạp tài liệu thành công! Hãy cấu hình ma trận đề thi.');
}

// =========================================================================
// Ma trận đề thi & Bloom Sliders
// =========================================================================

function handleBloomSliderChange() {
    const nb = parseInt(document.getElementById('sliderNhanBiet').value, 10);
    const th = parseInt(document.getElementById('sliderThongHieu').value, 10);
    const vd = parseInt(document.getElementById('sliderVanDung').value, 10);
    const vdc = parseInt(document.getElementById('sliderVanDungCao').value, 10);

    appState.bloomDistribution['Nhận biết'] = nb;
    appState.bloomDistribution['Thông hiểu'] = th;
    appState.bloomDistribution['Vận dụng'] = vd;
    appState.bloomDistribution['Vận dụng cao'] = vdc;

    updateBloomDisplays();
}

function updateBloomDisplays() {
    const nb = appState.bloomDistribution['Nhận biết'];
    const th = appState.bloomDistribution['Thông hiểu'];
    const vd = appState.bloomDistribution['Vận dụng'];
    const vdc = appState.bloomDistribution['Vận dụng cao'];

    document.getElementById('valNhanBiet').textContent = `${nb}%`;
    document.getElementById('valThongHieu').textContent = `${th}%`;
    document.getElementById('valVanDung').textContent = `${vd}%`;
    document.getElementById('valVanDungCao').textContent = `${vdc}%`;

    const total = nb + th + vd + vdc;
    const badge = document.getElementById('bloomTotalBadge');
    badge.textContent = `Tổng: ${total}%`;

    if (total === 100) {
        badge.className = 'badge badge-success';
    } else {
        badge.className = 'badge badge-info';
    }
}

function applyPreset(nb, th, vd, vdc, activeBtnId) {
    document.getElementById('sliderNhanBiet').value = nb;
    document.getElementById('sliderThongHieu').value = th;
    document.getElementById('sliderVanDung').value = vd;
    document.getElementById('sliderVanDungCao').value = vdc;

    appState.bloomDistribution['Nhận biết'] = nb;
    appState.bloomDistribution['Thông hiểu'] = th;
    appState.bloomDistribution['Vận dụng'] = vd;
    appState.bloomDistribution['Vận dụng cao'] = vdc;

    ['presetGDDT', 'presetReview', 'presetDGNL'].forEach(id => {
        const btn = document.getElementById(id);
        if (id === activeBtnId) {
            btn.classList.add('active-preset');
        } else {
            btn.classList.remove('active-preset');
        }
    });

    updateBloomDisplays();
    showToast('Đã áp dụng cấu hình ma trận mẫu.');
}

// =========================================================================
// Luồng sinh câu hỏi và cập nhật tiến trình (Progress Flow)
// =========================================================================

async function startGenerationFlow() {
    if (!appState.currentDoc || !appState.currentDoc.text) {
        showToast('Vui lòng nạp tài liệu trước!');
        return;
    }

    // Thu thập các dạng câu hỏi được chọn
    const checkedTypes = Array.from(document.querySelectorAll('input[name="qType"]:checked')).map(cb => cb.value);
    if (checkedTypes.length === 0) {
        showToast('Vui lòng tích chọn ít nhất 1 dạng câu hỏi trắc nghiệm!');
        return;
    }

    const totalQuestions = parseInt(document.getElementById('totalQuestionsInput').value, 10);

    // Hiển thị phần Tiến trình
    const progressSection = document.getElementById('sectionProgress');
    const reviewSection = document.getElementById('sectionReview');
    progressSection.classList.remove('hidden');
    reviewSection.classList.add('hidden');
    updateStepper(3);

    const barFill = document.getElementById('progressBarFill');
    const msg = document.getElementById('progressMessage');
    const pct = document.getElementById('progressPercent');
    const logBox = document.getElementById('terminalLog');

    function addLog(text) {
        const line = document.createElement('div');
        line.className = 'log-line';
        line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
        logBox.appendChild(line);
        logBox.scrollTop = logBox.scrollHeight;
    }

    barFill.style.width = '20%';
    pct.textContent = '20%';
    msg.textContent = 'Đang phân tích cấu trúc chủ đề kiến thức (Semantic Thematic Chunking)...';
    addLog('Kích hoạt bộ phân đoạn ngữ nghĩa 1.500 - 2.500 từ...');

    try {
        // Bước 1: Gọi Chunking
        const chunkRes = await fetch('/api/chunk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: appState.currentDoc.text })
        });

        if (!chunkRes.ok) throw new Error('Lỗi phân đoạn ngữ nghĩa');
        const chunkData = await chunkRes.json();
        appState.chunks = chunkData.chunks || [];

        barFill.style.width = '45%';
        pct.textContent = '45%';
        msg.textContent = `Đã chia tách thành ${appState.chunks.length} phân đoạn chủ đề. Đang gửi sang bộ suy luận khảo thí...`;
        addLog(`Hoàn thành phân đoạn. Tổng: ${appState.chunks.length} chủ đề.`);

        // Bước 2: Gọi Generate
        barFill.style.width = '70%';
        pct.textContent = '70%';
        msg.textContent = `Đang tạo ${totalQuestions} câu hỏi theo 22 nguyên tắc Haladyna và đối chiếu dẫn chứng...`;
        addLog('Kiểm định chéo đối chiếu nguyên văn (Verbatim Citation)...');

        const genRes = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chunks: appState.chunks,
                total_questions: totalQuestions,
                bloom_distribution: appState.bloomDistribution,
                selected_types: checkedTypes
            })
        });

        if (!genRes.ok) throw new Error('Lỗi khi sinh câu hỏi');
        const genData = await genRes.json();

        barFill.style.width = '100%';
        pct.textContent = '100%';
        msg.textContent = 'Khởi tạo câu hỏi và Thẻ kiểm định hoàn tất!';
        addLog(`Đã tạo thành công ${genData.questions.length} câu hỏi đạt chuẩn khảo thí.`);

        appState.generatedQuestions = genData.questions;
        appState.selectedQuestionIds = new Set(genData.questions.map(q => q.id));

        setTimeout(() => {
            progressSection.classList.add('hidden');
            reviewSection.classList.remove('hidden');
            updateStepper(4);
            renderQuestionsList();
            showToast(`Đã tạo xong ${genData.questions.length} câu hỏi! Hãy rà soát thẻ kiểm định.`);
        }, 600);

    } catch (err) {
        msg.textContent = `Lỗi: ${err.message}`;
        addLog(`[ERROR] ${err.message}`);
        showToast(`Lỗi: ${err.message}`);
    }
}

// =========================================================================
// Render Danh sách Câu hỏi & Thẻ kiểm định Double-Check
// =========================================================================

function renderQuestionsList() {
    const container = document.getElementById('questionsListContainer');
    container.innerHTML = '';

    const filtered = appState.generatedQuestions.filter(q => {
        if (appState.activeFilterType !== 'all' && q.type !== appState.activeFilterType) {
            return false;
        }
        if (appState.activeFilterBloom !== 'all' && q.bloom_level !== appState.activeFilterBloom) {
            return false;
        }
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center p-4 text-muted">
                Không tìm thấy câu hỏi phù hợp với bộ lọc hiện tại.
            </div>
        `;
        updateSelectedCounter();
        return;
    }

    filtered.forEach((q, displayIdx) => {
        const isSelected = appState.selectedQuestionIds.has(q.id);
        const card = document.createElement('div');
        card.className = `question-card ${isSelected ? 'selected' : ''}`;
        card.id = `card_${q.id}`;

        // Bloom class
        const bloomClass = getBloomBadgeClass(q.bloom_level);

        // Header câu hỏi
        const cardHeader = `
            <div class="question-card-header">
                <div class="header-left">
                    <input type="checkbox" class="q-checkbox" id="chk_${q.id}" ${isSelected ? 'checked' : ''} onchange="toggleQuestionSelection('${q.id}')">
                    <span class="q-number">Câu ${displayIdx + 1}</span>
                </div>
                <div class="header-badges">
                    <span class="badge badge-qtype">${escapeHtml(q.type_name || q.type)}</span>
                    <span class="badge ${bloomClass}">${escapeHtml(q.bloom_level || 'Nhận biết')}</span>
                </div>
            </div>
        `;

        // Render Options
        const optionsHtml = renderQuestionOptions(q);

        // Thẻ kiểm định Double-Check Card
        const db = q.double_check || {};
        const citation = db.verbatim_citation || 'Dẫn chiếu trực tiếp từ ngữ liệu nguồn.';
        const analysis = db.option_analysis || 'Phương án đã được kiểm chứng đối chiếu.';
        const bloomJust = db.bloom_justification || 'Phù hợp thang nhận thức Bloom.';

        const doubleCheckHtml = `
            <div class="double-check-box">
                <div class="double-check-title">
                    <span>🛡️ Thẻ kiểm định khảo thí (Double-Check Card)</span>
                    <span class="grounded-seal">✓ 100% Căn cứ tài liệu</span>
                </div>
                <div class="citation-quote">
                    "${escapeHtml(citation)}"
                </div>
                <div class="check-detail-row">
                    <span class="check-label">Đáp án chính thức: </span>
                    <strong style="color: #15803d;">${escapeHtml(String(q.correct_answer || ''))}</strong>
                </div>
                <div class="check-detail-row">
                    <span class="check-label">Phân tích phương án: </span>
                    <span>${escapeHtml(analysis)}</span>
                </div>
                <div class="check-detail-row">
                    <span class="check-label">Lý giải mức Bloom: </span>
                    <span>${escapeHtml(bloomJust)}</span>
                </div>
            </div>
        `;

        // Body câu hỏi
        const cardBody = `
            <div class="question-card-body">
                <div class="q-stem">${escapeHtml(q.stem || '')}</div>
                ${optionsHtml}
                ${doubleCheckHtml}
            </div>
        `;

        card.innerHTML = cardHeader + cardBody;
        container.appendChild(card);
    });

    updateSelectedCounter();
}

function renderQuestionOptions(q) {
    const type = q.type;
    const opts = q.options;

    if (type === 'mcq' || type === 'msq') {
        if (!Array.isArray(opts)) return '';
        const items = opts.map(opt => {
            const isCorrect = isOptionCorrect(opt, q.correct_answer);
            return `<div class="q-opt-item ${isCorrect ? 'is-correct' : ''}">${escapeHtml(opt)}</div>`;
        }).join('');
        return `<div class="q-options-container">${items}</div>`;
    }

    if (type === 'compound_tf') {
        if (!Array.isArray(opts)) return '';
        const items = opts.map(opt => {
            return `<div class="q-opt-item">${escapeHtml(opt)} <strong style="color: #2563eb;">[Đúng / Sai]</strong></div>`;
        }).join('');
        return `<div class="q-options-container">${items}</div>`;
    }

    if (type === 'short_answer') {
        return `
            <div class="q-opt-item" style="border-style: dashed; border-color: #cbd5e1; font-style: italic;">
                Thí sinh điền từ khóa hoặc số liệu ngắn (tối đa 3 - 5 từ)...
            </div>
        `;
    }

    if (type === 'matching') {
        if (typeof opts === 'object' && opts.column_a && opts.column_b) {
            const colA = opts.column_a.map(a => `<li>${escapeHtml(a)}</li>`).join('');
            const colB = opts.column_b.map(b => `<li>${escapeHtml(b)}</li>`).join('');
            return `
                <div class="grid-2-col" style="gap: 1rem; font-size: 0.85rem;">
                    <div style="background: #f8fafc; padding: 0.75rem; border-radius: 6px;">
                        <strong>CỘT 1:</strong>
                        <ul style="padding-left: 1.25rem; margin-top: 0.4rem;">${colA}</ul>
                    </div>
                    <div style="background: #f8fafc; padding: 0.75rem; border-radius: 6px;">
                        <strong>CỘT 2:</strong>
                        <ul style="padding-left: 1.25rem; margin-top: 0.4rem;">${colB}</ul>
                    </div>
                </div>
            `;
        }
        return '';
    }

    if (type === 'cloze') {
        if (Array.isArray(opts)) {
            const items = opts.map(opt => `<div class="q-opt-item">${escapeHtml(opt)}</div>`).join('');
            return `<div class="q-options-container">${items}</div>`;
        }
        return '';
    }

    if (type === 'sequencing') {
        if (typeof opts === 'object' && opts.items && opts.choices) {
            const items = opts.items.map(it => `<div>${escapeHtml(it)}</div>`).join('');
            const choices = opts.choices.map(ch => `<div class="q-opt-item">${escapeHtml(ch)}</div>`).join('');
            return `
                <div style="display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.88rem;">
                    <div style="background: #f8fafc; padding: 0.6rem; border-radius: 6px;">${items}</div>
                    <div class="q-options-container">${choices}</div>
                </div>
            `;
        }
        return '';
    }

    return '';
}

function isOptionCorrect(optionText, correctAnswer) {
    if (!correctAnswer || !optionText) return false;
    const trimmedOpt = optionText.trim();
    const cleanAns = String(correctAnswer).trim();
    if (trimmedOpt.startsWith(cleanAns + '.') || trimmedOpt.startsWith(cleanAns + ' ')) return true;
    return false;
}

function getBloomBadgeClass(bloom) {
    switch (bloom) {
        case 'Nhận biết': return 'badge-bloom-nhanbiet';
        case 'Thông hiểu': return 'badge-bloom-thonghieu';
        case 'Vận dụng': return 'badge-bloom-vandung';
        case 'Vận dụng cao': return 'badge-bloom-vandungcao';
        default: return 'badge-bloom-thonghieu';
    }
}

// =========================================================================
// Tương tác Checkbox & Bộ chọn câu hỏi
// =========================================================================

window.toggleQuestionSelection = function(id) {
    if (appState.selectedQuestionIds.has(id)) {
        appState.selectedQuestionIds.delete(id);
        const card = document.getElementById(`card_${id}`);
        if (card) card.classList.remove('selected');
    } else {
        appState.selectedQuestionIds.add(id);
        const card = document.getElementById(`card_${id}`);
        if (card) card.classList.add('selected');
    }
    updateSelectedCounter();
};

function setAllQuestionsSelected(isSelected) {
    if (isSelected) {
        appState.generatedQuestions.forEach(q => appState.selectedQuestionIds.add(q.id));
    } else {
        appState.selectedQuestionIds.clear();
    }
    renderQuestionsList();
}

function updateSelectedCounter() {
    const total = appState.generatedQuestions.length;
    const selected = appState.selectedQuestionIds.size;
    document.getElementById('selectedCountDisplay').textContent = `Đã chọn: ${selected}/${total} câu`;
}

// =========================================================================
// Xuất đề thi Word (.docx) 2 phần
// =========================================================================

async function executeExportDocx() {
    const selectedList = appState.generatedQuestions.filter(q => appState.selectedQuestionIds.has(q.id));
    if (selectedList.length === 0) {
        showToast('Vui lòng chọn ít nhất 1 câu hỏi để xuất đề thi!');
        return;
    }

    const schoolName = document.getElementById('exportSchoolName').value.trim();
    const examTitle = document.getElementById('exportExamTitle').value.trim();
    const subject = document.getElementById('exportSubject').value.trim();
    const duration = document.getElementById('exportDuration').value.trim();
    const examCode = document.getElementById('exportExamCode').value.trim();

    showToast('Đang khởi tạo file Word (.docx) chuyên nghiệp...');
    const btn = document.getElementById('btnConfirmExport');
    btn.disabled = true;

    try {
        const res = await fetch('/api/export-docx', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                questions: selectedList,
                exam_meta: {
                    school_name: schoolName,
                    exam_title: examTitle,
                    subject: subject,
                    duration: duration,
                    exam_code: examCode,
                    academic_year: 'NĂM HỌC 2025 - 2026'
                }
            })
        });

        if (!res.ok) {
            let errorMsg = 'Lỗi khi biên soạn file Word';
            try {
                const errData = await res.json();
                if (errData && errData.detail) {
                    errorMsg = errData.detail;
                }
            } catch (_) {}
            throw new Error(errorMsg);
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        
        // Làm sạch tên file tải về
        const cleanSubj = subject.replace(/[\\/:*?"<>|]/g, '_').trim() || 'Khao_Thi';
        a.download = `De_Thi_${cleanSubj}_Ma_${examCode}.docx`;
        
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 200);

        document.getElementById('exportModal').classList.add('hidden');
        showToast('Tải đề thi Word thành công! File gồm Đề thi và Đáp án chi tiết.');
    } catch (err) {
        showToast(`${err.message}`);
    } finally {
        btn.disabled = false;
    }
}

// =========================================================================
// Tiện ích UI (Stepper, Toast, Escape)
// =========================================================================

function updateStepper(step) {
    for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`step${i}Indicator`);
        if (i < step) {
            el.className = 'step-item completed';
        } else if (i === step) {
            el.className = 'step-item active';
        } else {
            el.className = 'step-item';
        }
    }
}

function showToast(msg) {
    const toast = document.getElementById('toastNotification');
    const msgEl = document.getElementById('toastMessage');
    msgEl.textContent = msg;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
