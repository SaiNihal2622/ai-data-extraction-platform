/**
 * Mindrift — AI Data Production & Validation Platform
 * ====================================================
 * Frontend logic for pipeline dashboard: single/batch scraping,
 * pipeline step animation, validation, and multi-format export.
 */

// ─── State ──────────────────────────────────────────────
let currentJobId = null;
let currentData = [];
let isBatchMode = false;

// ─── API Base URL ───────────────────────────────────────
const API_BASE = window.location.origin;

// ─── DOM References ─────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── Initialization ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();

    // Enter key in URL input
    $('#urlInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startPipeline();
    });

    // Batch mode toggle
    $('#batchToggle').addEventListener('change', (e) => {
        isBatchMode = e.target.checked;
        $('#singleUrlGroup').style.display = isBatchMode ? 'none' : 'block';
        $('#batchUrlGroup').style.display = isBatchMode ? 'block' : 'none';
    });
});

// ─── Health Check ───────────────────────────────────────
async function checkHealth() {
    const badge = $('#healthBadge');
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        const data = await res.json();
        badge.className = 'health-badge online';
        badge.innerHTML = `<span class="health-dot"></span>${data.status === 'healthy' ? 'System Online' : data.status}`;
    } catch {
        badge.className = 'health-badge offline';
        badge.innerHTML = '<span class="health-dot"></span>Offline';
    }
}

// ─── Main Pipeline Entry ─────────────────────────────────
async function startPipeline() {
    if (isBatchMode) {
        await startBatchScrape();
    } else {
        await startScrape();
    }
}

// ─── Single URL Scrape ──────────────────────────────────
async function startScrape() {
    const url = $('#urlInput').value.trim();
    if (!url) { $('#urlInput').focus(); return; }
    try { new URL(url); } catch {
        showError('Please enter a valid URL (e.g., https://example.com)');
        return;
    }

    const useDynamic = $('#dynamicToggle').checked;
    const useLLM = $('#llmToggle').checked;
    const maxPages = parseInt($('#maxPages').value) || 5;

    showLoading();
    activateStep('collect');

    try {
        animateProgress();
        activateStep('collect');

        const res = await fetch(`${API_BASE}/api/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, use_dynamic: useDynamic, use_llm: useLLM, max_pages: maxPages }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Server error (${res.status})`);
        }

        completeStep('collect');
        activateStep('process');
        await sleep(300);
        completeStep('process');
        activateStep('validate');
        await sleep(300);

        const data = await res.json();
        currentJobId = data.job_id;
        currentData = data.data || [];

        completeStep('validate');
        activateStep('export');
        await sleep(200);
        completeStep('export');

        showResults(data);

    } catch (err) {
        resetSteps();
        showError(err.message || 'An unexpected error occurred');
    }
}

// ─── Batch Scrape ───────────────────────────────────────
async function startBatchScrape() {
    const text = $('#batchUrls').value.trim();
    if (!text) { $('#batchUrls').focus(); return; }

    const urls = text.split('\n').map(u => u.trim()).filter(u => u.length > 0);
    if (urls.length === 0) {
        showError('Please enter at least one URL');
        return;
    }

    const useDynamic = $('#dynamicToggle').checked;
    const useLLM = $('#llmToggle').checked;
    const maxPages = parseInt($('#maxPages').value) || 3;

    showLoading(true, urls.length);
    activateStep('collect');

    try {
        animateProgress();

        const res = await fetch(`${API_BASE}/api/batch-scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls, use_dynamic: useDynamic, use_llm: useLLM, max_pages: maxPages }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Server error (${res.status})`);
        }

        completeStep('collect');
        activateStep('process');
        await sleep(300);
        completeStep('process');
        activateStep('validate');
        await sleep(300);

        const data = await res.json();
        currentData = data.data || [];
        currentJobId = null; // batch doesn't have single job_id

        completeStep('validate');
        activateStep('export');
        await sleep(200);
        completeStep('export');

        showBatchResults(data);

    } catch (err) {
        resetSteps();
        showError(err.message || 'Batch processing failed');
    }
}

// ─── Pipeline Steps ─────────────────────────────────────
function activateStep(stepName) {
    const step = $(`.pipeline-step[data-step="${stepName}"]`);
    if (step) step.className = 'pipeline-step active';
    // Activate connector before this step
    const steps = ['collect', 'process', 'validate', 'export'];
    const idx = steps.indexOf(stepName);
    if (idx > 0) {
        const connectors = $$('.step-connector');
        if (connectors[idx - 1]) connectors[idx - 1].className = 'step-connector active';
    }
}

function completeStep(stepName) {
    const step = $(`.pipeline-step[data-step="${stepName}"]`);
    if (step) step.className = 'pipeline-step completed';
}

function resetSteps() {
    $$('.pipeline-step').forEach(s => s.className = 'pipeline-step');
    $$('.step-connector').forEach(c => c.className = 'step-connector');
}

// ─── UI State Functions ──────────────────────────────────
function showLoading(batch = false, totalUrls = 0) {
    $('#inputCard').style.display = 'none';
    $('#loadingCard').style.display = 'block';
    $('#errorCard').style.display = 'none';
    $('#resultsSection').style.display = 'none';
    updateLoadingText(batch ? `Processing ${totalUrls} URLs...` : 'Connecting to target website...');

    if (batch) {
        $('#batchProgress').style.display = 'block';
        $('#batchProgressText').textContent = `Processing ${totalUrls} URLs...`;
    } else {
        $('#batchProgress').style.display = 'none';
    }
}

function showError(message) {
    $('#inputCard').style.display = 'block';
    $('#loadingCard').style.display = 'none';
    $('#errorCard').style.display = 'block';
    $('#resultsSection').style.display = 'none';
    $('#errorText').textContent = message;
    clearInterval(progressInterval);
}

function showResults(data) {
    $('#inputCard').style.display = 'block';
    $('#loadingCard').style.display = 'none';
    $('#errorCard').style.display = 'none';
    $('#resultsSection').style.display = 'block';
    clearInterval(progressInterval);

    const validation = data.validation || {};

    // Stats
    $('#statPages').textContent = data.pages_crawled || 0;
    $('#statItems').textContent = data.items_extracted || 0;
    $('#statValid').textContent = validation.valid_records ?? data.items_extracted ?? 0;
    $('#statInvalid').textContent = validation.invalid_records ?? 0;

    // Hide batch results
    $('#batchResultsCard').style.display = 'none';

    // AI Summary
    renderAI(data);

    // Data table
    renderTable(data.data || []);

    // Validation
    renderValidation(validation);

    // Scroll to results
    $('#resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showBatchResults(data) {
    $('#inputCard').style.display = 'block';
    $('#loadingCard').style.display = 'none';
    $('#errorCard').style.display = 'none';
    $('#resultsSection').style.display = 'block';
    clearInterval(progressInterval);

    const validation = data.validation || {};

    // Stats
    $('#statPages').textContent = data.completed || 0;
    $('#statItems').textContent = data.total_items || 0;
    $('#statValid').textContent = validation.valid_records ?? 0;
    $('#statInvalid').textContent = validation.invalid_records ?? 0;

    // Batch URL results
    renderBatchUrlResults(data.url_results || []);

    // AI Summary
    renderAI(data);

    // Data table
    renderTable(data.data || []);

    // Validation
    renderValidation(validation);

    $('#resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetUI() {
    $('#inputCard').style.display = 'block';
    $('#loadingCard').style.display = 'none';
    $('#errorCard').style.display = 'none';
    $('#resultsSection').style.display = 'none';
    currentJobId = null;
    currentData = [];
    resetSteps();
    clearInterval(progressInterval);
}

// ─── Loading Animation ──────────────────────────────────
let progressInterval = null;

function animateProgress() {
    const fill = $('#progressFill');
    let width = 0;
    const messages = [
        'Connecting to target website...',
        'Fetching page content...',
        'Parsing HTML structure...',
        'Extracting data patterns...',
        'Processing and cleaning data...',
        'Running validation checks...',
        'Generating quality report...',
    ];
    let msgIndex = 0;

    clearInterval(progressInterval);
    progressInterval = setInterval(() => {
        width = Math.min(width + Math.random() * 10 + 2, 92);
        fill.style.width = width + '%';

        if (width > (msgIndex + 1) * (90 / messages.length) && msgIndex < messages.length - 1) {
            msgIndex++;
            updateLoadingText(messages[msgIndex]);
        }
    }, 700);
}

function updateLoadingText(text) {
    $('#loadingText').textContent = text;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ─── Batch URL Results ───────────────────────────────────
function renderBatchUrlResults(results) {
    const card = $('#batchResultsCard');
    const list = $('#batchUrlList');
    list.innerHTML = '';

    if (!results || results.length === 0) {
        card.style.display = 'none';
        return;
    }

    card.style.display = 'block';
    results.forEach(r => {
        const div = document.createElement('div');
        div.className = `batch-url-item ${r.status}`;

        const status = document.createElement('span');
        status.className = `batch-url-status ${r.status}`;
        status.textContent = r.status === 'success' ? '✓' : '✗';

        const url = document.createElement('span');
        url.className = 'batch-url-text';
        url.textContent = r.url;

        const items = document.createElement('span');
        items.className = 'batch-url-items';
        items.textContent = r.status === 'success' ? `${r.items_extracted} items` : (r.error || 'failed');

        div.appendChild(status);
        div.appendChild(url);
        div.appendChild(items);
        list.appendChild(div);
    });
}

// ─── AI Rendering ────────────────────────────────────────
function renderAI(data) {
    if (data.ai_summary) {
        $('#aiSummaryCard').style.display = 'block';
        $('#aiSummaryText').textContent = data.ai_summary;

        if (data.ai_quality_score && data.ai_quality_score.score) {
            const score = data.ai_quality_score;
            $('#qualityBadge').style.display = 'inline-block';
            $('#qualityBadge').textContent = `${score.score} / 10`;

            const details = $('#aiQualityDetails');
            details.style.display = 'block';
            let html = '';
            if (score.justification) {
                html += `<p style="margin-bottom:8px;">${score.justification}</p>`;
            }
            if (score.issues && score.issues.length) {
                html += '<ul>';
                score.issues.forEach(i => { html += `<li>⚠ ${i}</li>`; });
                html += '</ul>';
            }
            if (score.suggestions && score.suggestions.length) {
                html += '<ul>';
                score.suggestions.forEach(s => { html += `<li>💡 ${s}</li>`; });
                html += '</ul>';
            }
            details.innerHTML = html;
        } else {
            $('#qualityBadge').style.display = 'none';
            $('#aiQualityDetails').style.display = 'none';
        }
    } else {
        $('#aiSummaryCard').style.display = 'none';
    }
}

// ─── Data Table Rendering ────────────────────────────────
function renderTable(items) {
    const thead = $('#tableHead');
    const tbody = $('#tableBody');
    const note = $('#tableNote');

    thead.innerHTML = '';
    tbody.innerHTML = '';

    if (!items || items.length === 0) {
        note.textContent = 'No data extracted.';
        return;
    }

    const excludeFields = new Set(['_source_url', 'structured_data', 'images', 'lists', 'links', 'paragraphs', 'tables', 'extracted_items']);
    const allKeys = new Set();
    items.forEach(item => {
        Object.keys(item).forEach(k => {
            if (!excludeFields.has(k)) allKeys.add(k);
        });
    });
    const columns = Array.from(allKeys).slice(0, 10);

    const headerRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = formatColumnName(col);
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    const displayItems = items.slice(0, 100);
    displayItems.forEach(item => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            let val = item[col];
            if (val === null || val === undefined) {
                td.textContent = '—';
                td.style.color = 'var(--text-muted)';
            } else if (typeof val === 'object') {
                td.textContent = JSON.stringify(val).slice(0, 100);
            } else {
                val = String(val);
                if (val.startsWith('http')) {
                    const a = document.createElement('a');
                    a.href = val;
                    a.textContent = val.length > 50 ? val.slice(0, 50) + '...' : val;
                    a.target = '_blank';
                    a.style.color = 'var(--accent-blue)';
                    a.style.textDecoration = 'none';
                    td.appendChild(a);
                } else {
                    td.textContent = val.length > 100 ? val.slice(0, 100) + '...' : val;
                }
            }
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    if (items.length > 100) {
        note.textContent = `Showing 100 of ${items.length} records. Download the full dataset using export.`;
    } else {
        note.textContent = `${items.length} record${items.length !== 1 ? 's' : ''} total.`;
    }
}

function formatColumnName(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .trim()
        .split(' ')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
        .join(' ');
}

// ─── Validation Rendering ────────────────────────────────
function renderValidation(validation) {
    const badge = $('#validationBadge');
    const stats = $('#validationStats');
    const list = $('#issuesList');
    const validBar = $('#validBar');
    const invalidBar = $('#invalidBar');

    stats.innerHTML = '';
    list.innerHTML = '';

    if (!validation || validation.total_records === undefined) {
        badge.className = 'validation-badge';
        badge.textContent = 'N/A';
        validBar.style.width = '0%';
        invalidBar.style.width = '0%';
        return;
    }

    // Validation summary bar
    const total = validation.total_records || 1;
    const validPct = ((validation.valid_records || 0) / total) * 100;
    const invalidPct = ((validation.invalid_records || 0) / total) * 100;
    validBar.style.width = validPct + '%';
    invalidBar.style.width = invalidPct + '%';

    // Badge
    if (validation.is_valid) {
        badge.className = 'validation-badge pass';
        badge.textContent = '✓ PASSED';
    } else if (validation.error_count > 0) {
        badge.className = 'validation-badge fail';
        badge.textContent = `${validation.error_count} ERROR${validation.error_count !== 1 ? 'S' : ''}`;
    } else {
        badge.className = 'validation-badge warn';
        badge.textContent = `${validation.warning_count} WARNING${validation.warning_count !== 1 ? 'S' : ''}`;
    }

    // Stats
    stats.innerHTML = `
        <span><strong>${validation.valid_records ?? '—'}</strong> valid</span>
        <span><strong>${validation.invalid_records ?? '—'}</strong> invalid</span>
        <span><strong>${validation.total_fields}</strong> fields</span>
        <span><strong>${validation.error_count || 0}</strong> errors</span>
        <span><strong>${validation.warning_count || 0}</strong> warnings</span>
    `;

    // Issues
    const issues = validation.issues || [];
    if (issues.length === 0) {
        list.innerHTML = '<p style="color:var(--accent-green);font-size:0.9rem;">✓ All validation checks passed — dataset is production-ready.</p>';
        return;
    }

    issues.slice(0, 20).forEach(issue => {
        const div = document.createElement('div');
        div.className = `issue-item ${issue.type}`;

        const tag = document.createElement('span');
        tag.className = `issue-tag ${issue.type}`;
        tag.textContent = issue.type;

        const msg = document.createElement('span');
        msg.className = 'issue-msg';
        msg.textContent = `${issue.message}${issue.affected_rows > 0 ? ` (${issue.affected_rows} rows)` : ''}`;

        div.appendChild(tag);
        div.appendChild(msg);
        list.appendChild(div);
    });

    if (issues.length > 20) {
        const more = document.createElement('p');
        more.style.cssText = 'color:var(--text-muted);font-size:0.85rem;margin-top:8px;';
        more.textContent = `... and ${issues.length - 20} more issues`;
        list.appendChild(more);
    }
}

// ─── Export ──────────────────────────────────────────────
async function exportData(format) {
    if (!currentJobId) {
        if (currentData.length === 0) return;
        if (format === 'json') {
            downloadBlob(JSON.stringify(currentData, null, 2), 'application/json', 'mindrift_export.json');
        } else {
            downloadBlob(convertToCSV(currentData), 'text/csv', 'mindrift_export.csv');
        }
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/export/${currentJobId}?format=${format}`);
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mindrift_${currentJobId}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
    } catch {
        if (format === 'json') {
            downloadBlob(JSON.stringify(currentData, null, 2), 'application/json', 'mindrift_export.json');
        } else {
            downloadBlob(convertToCSV(currentData), 'text/csv', 'mindrift_export.csv');
        }
    }
}

function exportToSheets() {
    if (currentData.length === 0) return;
    const csv = convertToCSV(currentData);
    downloadBlob(csv, 'text/csv', 'mindrift_for_sheets.csv');
    // Open Google Sheets create page
    setTimeout(() => {
        window.open('https://sheets.google.com/create', '_blank');
    }, 500);
}

function downloadBlob(content, type, filename) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function convertToCSV(items) {
    if (!items || items.length === 0) return '';
    const keys = Array.from(new Set(items.flatMap(Object.keys)));
    const header = keys.map(escapeCSV).join(',');
    const rows = items.map(item =>
        keys.map(k => escapeCSV(item[k] ?? '')).join(',')
    );
    return [header, ...rows].join('\n');
}

function escapeCSV(val) {
    const str = String(val);
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
}
