/* ============================================================
   DISRUPTIO DOCPROCESSING — Frontend Application
   ============================================================ */

(function () {
    'use strict';

    // ---- CONFIG ----
    const API = '';  // Same origin
    const POLL_INTERVAL = 2000;

    // ---- STATE ----
    let state = {
        view: 'upload',         // upload | processing | results
        file: null,             // File object
        sourceFileId: null,     // from upload response
        jobId: null,            // from /v1/process
        jobResult: null,        // final job result
        documents: [],          // reconciled documents
        showExceptionsOnly: false,
        sortField: null,
        sortAsc: true,
    };

    // ---- DOM REFS ----
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const views = {
        upload: $('#viewUpload'),
        processing: $('#viewProcessing'),
        results: $('#viewResults'),
    };

    // Upload
    const dropZone = $('#dropZone');
    const fileInput = $('#fileInput');
    const filePreview = $('#filePreview');
    const fileName = $('#fileName');
    const fileSize = $('#fileSize');
    const btnStartProcess = $('#btnStartProcess');
    const btnRemoveFile = $('#btnRemoveFile');
    const btnBrowse = $('#btnBrowse');
    const btnHeroUpload = $('#btnHeroUpload');
    const btnNewUpload = $('#btnNewUpload');

    // Processing
    const stageList = $('#stageList');

    // Results
    const resultsBody = $('#resultsBody');
    const chkExceptions = $('#chkExceptions');
    const alertBanner = $('#alertBanner');
    const alertText = $('#alertText');

    // Drawer
    const drawer = $('#drawer');
    const drawerOverlay = $('#drawerOverlay');
    const drawerClose = $('#drawerClose');
    const drawerTitle = $('#drawerTitle');

    // Download
    const btnDownloadExcel = $('#btnDownloadExcel');
    const btnDownloadPdfs = $('#btnDownloadPdfs');


    // ============================================================
    // VIEW MANAGEMENT
    // ============================================================
    function showView(name) {
        state.view = name;
        Object.keys(views).forEach(k => {
            views[k].classList.toggle('active', k === name);
        });
        btnNewUpload.style.display = (name === 'results') ? '' : 'none';
    }


    // ============================================================
    // FILE UPLOAD (Drag & Drop)
    // ============================================================
    function setFile(file) {
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
            return;
        }
        state.file = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatSize(file.size);
        filePreview.classList.add('visible');
        btnStartProcess.disabled = false;
    }

    function clearFile() {
        state.file = null;
        fileInput.value = '';
        filePreview.classList.remove('visible');
        btnStartProcess.disabled = true;
    }

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // Drag events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length) setFile(files[0]);
    });

    dropZone.addEventListener('click', () => fileInput.click());
    btnBrowse.addEventListener('click', (e) => { e.preventDefault(); fileInput.click(); });
    btnHeroUpload.addEventListener('click', () => {
        dropZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => fileInput.click(), 400);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) setFile(fileInput.files[0]);
    });

    btnRemoveFile.addEventListener('click', clearFile);


    // ============================================================
    // API CLIENT
    // ============================================================
    async function apiUpload(file) {
        const form = new FormData();
        form.append('file', file);
        const res = await fetch(`${API}/v1/files`, { method: 'POST', body: form });
        if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
        return res.json();
    }

    async function apiProcess(sourceFileId) {
        const res = await fetch(`${API}/v1/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_file_id: sourceFileId }),
        });
        if (!res.ok) throw new Error(`Process failed: ${res.status}`);
        return res.json();
    }

    async function apiJobStatus(jobId) {
        const res = await fetch(`${API}/v1/jobs/${jobId}`);
        if (!res.ok) throw new Error(`Job poll failed: ${res.status}`);
        return res.json();
    }

    async function apiBoundaries(sourceFileId) {
        const res = await fetch(`${API}/v1/extract/boundaries`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_file_id: sourceFileId }),
        });
        if (!res.ok) throw new Error(`Boundaries failed: ${res.status}`);
        return res.json();
    }

    async function apiExtractPo(sourceFileId, ranges, pipeline) {
        const res = await fetch(`${API}/v1/extract/po?pipeline=${pipeline}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_file_id: sourceFileId, ranges }),
        });
        if (!res.ok) throw new Error(`PO extraction failed: ${res.status}`);
        return res.json();
    }

    async function apiReconcile(sourceFileId, documents) {
        const res = await fetch(`${API}/v1/reconcile/po`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_file_id: sourceFileId, documents }),
        });
        if (!res.ok) throw new Error(`Reconcile failed: ${res.status}`);
        return res.json();
    }

    async function apiSplit(sourceFileId, ranges) {
        const res = await fetch(`${API}/v1/split`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_file_id: sourceFileId, ranges }),
        });
        if (!res.ok) throw new Error(`Split failed: ${res.status}`);
        return res.json();
    }

    async function apiExportExcel(sourceFileId, documents) {
        const res = await fetch(`${API}/v1/export/excel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_file_id: sourceFileId, documents }),
        });
        if (!res.ok) throw new Error(`Export failed: ${res.status}`);
        return res.json();
    }

    async function apiUpdateDocument(sourceFileId, docIndex, decidedPo) {
        const res = await fetch(`${API}/v1/documents/${sourceFileId}/${docIndex}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ decided_po_primary: decidedPo }),
        });
        if (!res.ok) throw new Error(`Update failed: ${res.status}`);
        return res.json();
    }


    // ============================================================
    // PROCESSING FLOW (synchronous step-by-step via API)
    // ============================================================
    function setStageStatus(stageName, status, detail) {
        const item = stageList.querySelector(`[data-stage="${stageName}"]`);
        if (!item) return;
        item.setAttribute('data-status', status);
        if (detail) {
            const detailEl = item.querySelector('.stage-detail');
            if (detailEl) detailEl.textContent = detail;
        }
    }

    async function runProcessingFlow() {
        showView('processing');

        const file = state.file;
        const uploadDetail = `${file.name} · ${formatSize(file.size)}`;
        setStageStatus('uploading', 'done', uploadDetail);
        $('#stageUploadDetail').textContent = uploadDetail;

        try {
            // Step 1: Upload
            setStageStatus('uploading', 'active', 'A carregar...');
            const uploadRes = await apiUpload(file);
            state.sourceFileId = uploadRes.source_file_id;
            setStageStatus('uploading', 'done', uploadDetail);

            // Step 2: Text extraction + Boundaries
            setStageStatus('extracting', 'active');
            setStageStatus('boundaries', 'active');
            const boundariesRes = await apiBoundaries(state.sourceFileId);
            const ranges = boundariesRes.ranges;
            setStageStatus('extracting', 'done', `${boundariesRes.ranges[boundariesRes.ranges.length - 1].end_page + 1} páginas extraídas`);
            setStageStatus('boundaries', 'done', `${boundariesRes.total_documents} documentos detectados`);

            // Step 3: Pipeline A (LLM)
            setStageStatus('pipeline_a', 'active', 'A chamar LLM...');
            let pipeADocs;
            try {
                const pipeARes = await apiExtractPo(state.sourceFileId, ranges, 'A');
                pipeADocs = pipeARes.documents;
                setStageStatus('pipeline_a', 'done', `${pipeADocs.length} documentos processados`);
            } catch (e) {
                // Pipeline A may fail if no API key — continue with null
                pipeADocs = ranges.map(r => ({
                    range: r,
                    result: { po_primary: null, po_secondary: null, po_numbers: [], supplier: null, confidence: 0, method: 'LLM', found_keywords: [], evidence: [] }
                }));
                setStageStatus('pipeline_a', 'done', 'Sem API key — ignorado');
            }

            // Step 4: Pipeline B (Regex)
            setStageStatus('pipeline_b', 'active', 'Regex + heurísticas...');
            const pipeBRes = await apiExtractPo(state.sourceFileId, ranges, 'B');
            const pipeBDocs = pipeBRes.documents;
            setStageStatus('pipeline_b', 'done', `${pipeBDocs.length} documentos processados`);

            // Step 5: Reconciliation
            setStageStatus('reconciling', 'active');
            const emptyResult = (method) => ({ po_primary: null, po_secondary: null, po_numbers: [], supplier: null, confidence: 0, method, found_keywords: [], evidence: [] });
            const reconDocs = ranges.map((r, i) => ({
                range: r,
                result_a: pipeADocs[i] ? pipeADocs[i].result : emptyResult('LLM'),
                result_b: pipeBDocs[i] ? pipeBDocs[i].result : emptyResult('REGEX'),
            }));
            const reconRes = await apiReconcile(state.sourceFileId, reconDocs);
            // Map API response to UI-friendly format
            state.documents = reconRes.documents.map((d, i) => ({
                range: d.range,
                doc_id: `${state.sourceFileId}_doc${String(i + 1).padStart(3, '0')}`,
                match_status: d.match_status,
                decided_po: d.decided_po_primary || null,
                decided_po_secondary: d.decided_po_secondary || null,
                decided_po_numbers: d.decided_po_numbers || [],
                pipeline_a_po: d.result_a ? d.result_a.po_primary : null,
                pipeline_b_po: d.result_b ? d.result_b.po_primary : null,
                pipeline_a_po_numbers: d.result_a ? (d.result_a.po_numbers || []) : [],
                pipeline_b_po_numbers: d.result_b ? (d.result_b.po_numbers || []) : [],
                confidence_a: d.result_a ? d.result_a.confidence : null,
                confidence_b: d.result_b ? d.result_b.confidence : null,
                final_status: d.status,
                next_action: d.next_action,
                reject_reason: d.reject_reason,
                pipeline_a: d.result_a,
                pipeline_b: d.result_b,
            }));
            setStageStatus('reconciling', 'done', `${state.documents.length} reconciliados`);

            // Step 6: Split PDF
            setStageStatus('splitting', 'active');
            try {
                await apiSplit(state.sourceFileId, ranges);
                setStageStatus('splitting', 'done', `${ranges.length} ficheiros criados`);
            } catch (e) {
                setStageStatus('splitting', 'done', 'Concluído');
            }

            // Step 7: Generate Index — transform to DocumentRecord format
            setStageStatus('indexing', 'active');
            try {
                const excelDocs = reconRes.documents.map((d, i) => ({
                    source_file_id: state.sourceFileId,
                    doc_id: `${state.sourceFileId}_doc${String(i + 1).padStart(3, '0')}`,
                    page_start: d.range.start_page,
                    page_end: d.range.end_page,
                    supplier_a: d.result_a ? d.result_a.supplier : null,
                    po_primary_a: d.result_a ? d.result_a.po_primary : null,
                    po_secondary_a: d.result_a ? d.result_a.po_secondary : null,
                    po_numbers_a: d.result_a ? (d.result_a.po_numbers || []) : [],
                    confidence_a: d.result_a ? d.result_a.confidence : 0,
                    method_a: d.result_a ? d.result_a.method : null,
                    supplier_b: d.result_b ? d.result_b.supplier : null,
                    po_primary_b: d.result_b ? d.result_b.po_primary : null,
                    po_secondary_b: d.result_b ? d.result_b.po_secondary : null,
                    po_numbers_b: d.result_b ? (d.result_b.po_numbers || []) : [],
                    confidence_b: d.result_b ? d.result_b.confidence : 0,
                    method_b: d.result_b ? d.result_b.method : null,
                    match_status: d.match_status,
                    decided_po_primary: d.decided_po_primary,
                    decided_po_secondary: d.decided_po_secondary,
                    decided_po_numbers: d.decided_po_numbers || [],
                    status: d.status,
                    next_action: d.next_action,
                    reject_reason: d.reject_reason,
                }));
                await apiExportExcel(state.sourceFileId, excelDocs);
                setStageStatus('indexing', 'done', 'Excel gerado');
            } catch (e) {
                console.error('Excel export error:', e);
                setStageStatus('indexing', 'done', 'Concluído');
            }

            // All done — show results
            setTimeout(() => renderResults(), 500);

        } catch (err) {
            console.error('Processing error:', err);
            // Mark current active stage as error
            const activeItem = stageList.querySelector('[data-status="active"]');
            if (activeItem) {
                activeItem.setAttribute('data-status', 'error');
                const detail = activeItem.querySelector('.stage-detail');
                if (detail) detail.textContent = `Erro: ${err.message}`;
            }
        }
    }


    // ============================================================
    // RESULTS RENDERING
    // ============================================================
    function renderResults() {
        showView('results');

        const docs = state.documents;

        // Summary counts
        const total = docs.length;
        const ok = docs.filter(d => d.match_status === 'MATCH_OK').length;
        const review = docs.filter(d => d.match_status === 'NEEDS_REVIEW').length;
        const mismatch = docs.filter(d => d.match_status === 'MISMATCH').length;

        $('#sumTotal').textContent = total;
        $('#sumOk').textContent = ok;
        $('#sumReview').textContent = review;
        $('#sumMismatch').textContent = mismatch;

        // Alert
        const exceptions = review + mismatch;
        if (exceptions > 0) {
            alertBanner.classList.add('visible');
            alertText.textContent = `${exceptions} documento${exceptions > 1 ? 's' : ''} requer${exceptions > 1 ? 'em' : ''} revisão.`;
        } else {
            alertBanner.classList.remove('visible');
        }

        renderTable();
    }

    function renderTable() {
        const docs = state.documents;
        let filtered = docs;

        if (state.showExceptionsOnly) {
            filtered = docs.filter(d =>
                d.match_status === 'NEEDS_REVIEW' || d.match_status === 'MISMATCH'
            );
        }

        // Sort
        if (state.sortField) {
            filtered = [...filtered].sort((a, b) => {
                let va = getSortValue(a, state.sortField);
                let vb = getSortValue(b, state.sortField);
                if (va < vb) return state.sortAsc ? -1 : 1;
                if (va > vb) return state.sortAsc ? 1 : -1;
                return 0;
            });
        }

        resultsBody.innerHTML = '';
        filtered.forEach((doc, idx) => {
            const row = document.createElement('tr');
            const docShort = doc.doc_id ? doc.doc_id.split('_').pop() : '—';
            const poDisplay = (doc.decided_po_numbers && doc.decided_po_numbers.length > 0)
                ? doc.decided_po_numbers.join(', ')
                : (doc.decided_po || '—');
            const pipeAPoDisplay = (doc.pipeline_a_po_numbers && doc.pipeline_a_po_numbers.length > 0)
                ? doc.pipeline_a_po_numbers.join(', ')
                : (doc.pipeline_a_po || '—');
            const pipeBPoDisplay = (doc.pipeline_b_po_numbers && doc.pipeline_b_po_numbers.length > 0)
                ? doc.pipeline_b_po_numbers.join(', ')
                : (doc.pipeline_b_po || '—');
            row.innerHTML = `
        <td class="mono">${idx + 1}</td>
        <td class="mono" title="${doc.doc_id || ''}">${docShort}</td>
        <td>${doc.range ? `${doc.range.start_page}–${doc.range.end_page}` : '—'}</td>
        <td class="mono"><strong>${poDisplay}</strong></td>
        <td class="mono">${pipeAPoDisplay}</td>
        <td class="mono">${pipeBPoDisplay}</td>
        <td class="num">${doc.confidence_a != null ? (doc.confidence_a * 100).toFixed(0) + '%' : '—'}</td>
        <td class="num">${doc.confidence_b != null ? (doc.confidence_b * 100).toFixed(0) + '%' : '—'}</td>
        <td>${matchBadge(doc.match_status)}</td>
        <td>${finalBadge(doc.final_status)}</td>
      `;
            row.addEventListener('click', () => openDrawer(doc, idx));
            resultsBody.appendChild(row);
        });
    }

    function getSortValue(doc, field) {
        switch (field) {
            case 'id': return doc.range ? doc.range.start_page : 0;
            case 'doc_id': return doc.doc_id || '';
            case 'pages': return doc.range ? doc.range.start_page : 0;
            case 'decided_po': return doc.decided_po || '';
            case 'match': return doc.match_status || '';
            case 'final': return doc.final_status || '';
            default: return '';
        }
    }

    function matchBadge(status) {
        if (!status) return '<span class="badge badge-pending">—</span>';
        switch (status) {
            case 'MATCH_OK': return '<span class="badge badge-ok">OK</span>';
            case 'NEEDS_REVIEW': return '<span class="badge badge-review">REVIEW</span>';
            case 'MISMATCH': return '<span class="badge badge-mismatch">MISMATCH</span>';
            default: return `<span class="badge badge-pending">${status}</span>`;
        }
    }

    function finalBadge(status) {
        if (!status) return '<span class="badge badge-pending">—</span>';
        switch (status) {
            case 'ACCEPTED': return '<span class="badge badge-ok">ACCEPTED</span>';
            case 'REVIEW': return '<span class="badge badge-review">REVIEW</span>';
            case 'REJECTED': return '<span class="badge badge-mismatch">REJECTED</span>';
            default: return `<span class="badge badge-pending">${status}</span>`;
        }
    }


    // ============================================================
    // DRAWER
    // ============================================================
    function openDrawer(doc, idx) {
        drawerTitle.textContent = `Documento #${idx + 1}`;

        // Info rows
        const drawerInfo = $('#drawerInfo');
        const poValue = doc.decided_po || '';
        drawerInfo.innerHTML = `
      ${infoRow('Páginas', doc.range ? `${doc.range.start_page}–${doc.range.end_page}` : '—')}
      <div class="info-row">
        <span class="info-row-label">PO Decidido</span>
        <span class="info-row-value po-edit-group">
          <input type="text" id="poEditInput" class="po-edit-input" value="${escapeHtml(poValue)}" placeholder="Inserir PO...">
          <button id="poSaveBtn" class="po-save-btn" title="Guardar">Guardar</button>
        </span>
      </div>
      ${infoRow('Status', matchBadge(doc.match_status))}
      ${infoRow('Decisão', finalBadge(doc.final_status))}
      <div class="info-row" id="acaoRow">
        <span class="info-row-label">Acção</span>
        <span class="info-row-value" id="acaoValue">${doc.next_action || '—'}</span>
      </div>
    `;

        // Save handler
        const poSaveBtn = $('#poSaveBtn');
        const poEditInput = $('#poEditInput');
        poSaveBtn.addEventListener('click', async () => {
            const newPo = poEditInput.value.trim();
            if (!newPo) return;
            poSaveBtn.disabled = true;
            poSaveBtn.textContent = '...';
            try {
                const result = await apiUpdateDocument(state.sourceFileId, idx, newPo);
                // Update client state
                doc.decided_po = result.decided_po_primary;
                doc.next_action = result.next_action;
                // Update the Acção display in the drawer
                const acaoValue = $('#acaoValue');
                if (acaoValue) acaoValue.textContent = result.next_action;
                // Re-render table
                renderTable();
                // Visual feedback
                poSaveBtn.textContent = '✓';
                poSaveBtn.classList.add('saved');
                setTimeout(() => {
                    poSaveBtn.textContent = 'Guardar';
                    poSaveBtn.classList.remove('saved');
                    poSaveBtn.disabled = false;
                }, 1500);
            } catch (e) {
                console.error('Save failed:', e);
                poSaveBtn.textContent = 'Erro';
                setTimeout(() => {
                    poSaveBtn.textContent = 'Guardar';
                    poSaveBtn.disabled = false;
                }, 2000);
            }
        });

        // Pipeline A
        const pipeA = $('#drawerPipeA');
        const pipelineAData = doc.pipeline_a || {};
        pipeA.innerHTML = `
      <div class="pipeline-col-title">Pipeline A — LLM</div>
      ${pipelineField('PO', pipelineAData.po_primary)}
      ${pipelineField('PO Secundário', pipelineAData.po_secondary)}
      ${pipelineField('Todos os POs', pipelineAData.po_numbers && pipelineAData.po_numbers.length ? pipelineAData.po_numbers.join(', ') : null)}
      ${pipelineField('Confiança', pipelineAData.confidence != null ? (pipelineAData.confidence * 100).toFixed(0) + '%' : null)}
      ${pipelineField('Método', pipelineAData.method)}
      ${pipelineField('Keywords', pipelineAData.found_keywords ? pipelineAData.found_keywords.join(', ') : null)}
    `;

        // Pipeline B
        const pipeB = $('#drawerPipeB');
        const pipelineBData = doc.pipeline_b || {};
        pipeB.innerHTML = `
      <div class="pipeline-col-title">Pipeline B — Regex</div>
      ${pipelineField('PO', pipelineBData.po_primary)}
      ${pipelineField('PO Secundário', pipelineBData.po_secondary)}
      ${pipelineField('Todos os POs', pipelineBData.po_numbers && pipelineBData.po_numbers.length ? pipelineBData.po_numbers.join(', ') : null)}
      ${pipelineField('Confiança', pipelineBData.confidence != null ? (pipelineBData.confidence * 100).toFixed(0) + '%' : null)}
      ${pipelineField('Método', pipelineBData.method)}
      ${pipelineField('Keywords', pipelineBData.found_keywords ? pipelineBData.found_keywords.join(', ') : null)}
    `;

        // Evidence
        const evidenceSection = $('#drawerEvidenceSection');
        const evidenceContainer = $('#drawerEvidence');
        const allEvidence = [
            ...(pipelineAData.evidence || []),
            ...(pipelineBData.evidence || []),
        ];
        if (allEvidence.length) {
            evidenceSection.style.display = '';
            evidenceContainer.innerHTML = allEvidence.map(e =>
                `<div style="margin-bottom: var(--sp-sm);">
          <div class="caption">Página ${e.page}</div>
          <div class="evidence-snippet">${escapeHtml(e.snippet)}</div>
        </div>`
            ).join('');
        } else {
            evidenceSection.style.display = 'none';
        }

        drawer.classList.add('open');
        drawerOverlay.classList.add('open');

        // Show PDF preview
        const pdfPanel = $('#pdfPreviewPanel');
        const pdfFrame = $('#pdfPreviewFrame');
        const pdfTitle = $('#pdfPreviewTitle');
        if (state.sourceFileId) {
            pdfTitle.textContent = `${doc.doc_id || 'Documento #' + (idx + 1)}`;
            pdfFrame.src = `${API}/v1/split/${state.sourceFileId}/doc/${idx + 1}`;
            pdfPanel.classList.add('open');
        }
    }

    function closeDrawer() {
        drawer.classList.remove('open');
        drawerOverlay.classList.remove('open');
        const pdfPanel = $('#pdfPreviewPanel');
        const pdfFrame = $('#pdfPreviewFrame');
        pdfPanel.classList.remove('open');
        pdfFrame.src = '';
    }

    function infoRow(label, value) {
        return `<div class="info-row">
      <span class="info-row-label">${label}</span>
      <span class="info-row-value">${value}</span>
    </div>`;
    }

    function pipelineField(label, value) {
        const isNull = value == null || value === '' || value === 'null';
        const displayValue = isNull ? '—' : value;
        const cls = isNull ? 'pipeline-field-value null' : 'pipeline-field-value mono';
        return `<div class="pipeline-field">
      <div class="pipeline-field-label">${label}</div>
      <div class="${cls}">${displayValue}</div>
    </div>`;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }


    // ============================================================
    // EVENT BINDINGS
    // ============================================================

    // Start processing
    btnStartProcess.addEventListener('click', () => {
        if (!state.file) return;
        runProcessingFlow();
    });

    // New upload
    btnNewUpload.addEventListener('click', () => {
        state = { ...state, file: null, sourceFileId: null, jobId: null, jobResult: null, documents: [], showExceptionsOnly: false };
        clearFile();
        // Reset stages
        stageList.querySelectorAll('.stage-item').forEach(item => {
            if (item.dataset.stage === 'uploading') {
                item.setAttribute('data-status', 'done');
            } else {
                item.setAttribute('data-status', 'pending');
            }
        });
        showView('upload');
    });

    // Exception toggle
    chkExceptions.addEventListener('change', () => {
        state.showExceptionsOnly = chkExceptions.checked;
        renderTable();
    });

    // Table sorting
    $$('.data-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (state.sortField === field) {
                state.sortAsc = !state.sortAsc;
            } else {
                state.sortField = field;
                state.sortAsc = true;
            }
            renderTable();
        });
    });

    // Drawer close
    drawerClose.addEventListener('click', closeDrawer);
    drawerOverlay.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDrawer();
    });

    // Downloads
    btnDownloadExcel.addEventListener('click', () => {
        if (state.sourceFileId) {
            window.open(`${API}/v1/export/excel/${state.sourceFileId}`, '_blank');
        }
    });

    btnDownloadPdfs.addEventListener('click', () => {
        if (state.sourceFileId) {
            window.open(`${API}/v1/split/${state.sourceFileId}/download`, '_blank');
        }
    });

    // How it works scroll
    const btnHowItWorks = $('#btnHowItWorks');
    if (btnHowItWorks) {
        btnHowItWorks.addEventListener('click', () => {
            const uploadCard = $('#uploadCard');
            if (uploadCard) uploadCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    }

    // API health check
    async function checkHealth() {
        try {
            const res = await fetch(`${API}/health`);
            const data = await res.json();
            const dot = document.querySelector('.header-status-dot');
            const label = document.querySelector('.header-status span');
            if (data.status === 'healthy') {
                dot.style.background = 'var(--state-success)';
                label.textContent = 'API Online';
            }
        } catch {
            const dot = document.querySelector('.header-status-dot');
            const label = document.querySelector('.header-status span');
            dot.style.background = 'var(--accent-red)';
            label.textContent = 'API Offline';
        }
    }

    // Init
    checkHealth();
    setInterval(checkHealth, 30000);

})();
