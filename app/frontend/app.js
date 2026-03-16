/**
 * MindRift — Frontend Application Logic
 * ======================================
 * Handles API communication, UI state management,
 * data rendering, and export functionality.
 */

// ─── State ──────────────────────────────────────────────
let currentJobId = null;
let currentData = [];

// ─── API Base URL ───────────────────────────────────────
const API_BASE = window.location.origin;

// ─── DOM References ─────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── Initialization ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    // Allow Enter key in URL input
    $('#urlInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startScrape();
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

// ─── Scrape Workflow ────────────────────────────────────
async function startScrape() {
    const url = $('#urlInput').value.trim();
    if (!url) {
        $('#urlInput').focus();
        return;
    }

    // Validate URL format
    try { new URL(url); } catch {
        showError('Please enter a valid URL (e.g., https://example.com)');
        return;
    }

    const useDynamic = $('#dynamicToggle').checked;
    const useLLM = $('#llmToggle').checked;
    const maxPages = parseInt($('#maxPages').value) || 5;

    // Show loading state
    showLoading();

    try {
        animateProgress();

        const res = await fetch(`${API_BASE}/api/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                use_dynamic: useDynamic,
                use_llm: useLLM,
                max_pages: maxPages,
            }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Server error (${res.status})`);
        }

        const data = await res.json();
        currentJobId = data.job_id;
        currentData = data.data || [];

        showResults(data);

    } catch (err) {
        showError(err.message || 'An unexpected error occurred');
    }
}

// ─── UI State Functions ──────────────────────────────────
function showLoading() {
    $('#inputCard').style.display = 'none';
    $('#loadingCard').style.display = 'block';
    $('#errorCard').style.display = 'none';
    $('#resultsSection').style.display = 'none';
    updateLoadingText('Connecting to target website...');
}

function showError(message) {
    $('#inputCard').style.display = 'block';
    $('#loadingCard').style.display = 'none';
    $('#errorCard').style.display = 'block';
    $('#resultsSection').style.display = 'none';
    $('#errorText').textContent = message;
}

function showResults(data) {
    $('#inputCard').style.display = 'block';
    $('#loadingCard').style.display = 'none';
    $('#errorCard').style.display = 'none';
    $('#resultsSection').style.display = 'block';

    // Update stats
    $('#statPages').textContent = data.pages_crawled || 0;
    $('#statItems').textContent = data.items_extracted || 0;
    $('#statMethod').textContent = (data.method || 'static').toUpperCase();

    const validation = data.validation || {};
    const issueCount = validation.total_issues || 0;
    $('#statIssues').textContent = issueCount;

    // AI Summary
    if (data.ai_summary) {
        $('#aiSummaryCard').style.display = 'block';
        $('#aiSummaryText').textContent = data.ai_summary;
    } else {
        $('#aiSummaryCard').style.display = 'none';
    }

    // Render data table
    renderTable(data.data || []);

    // Render validation report
    renderValidation(validation);

    // Scroll to results
    $('#resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetUI() {
    $('#inputCard').style.display = 'block';
    $('#loadingCard').style.display = 'none';
    $('#errorCard').style.display = 'none';
    $('#resultsSection').style.display = 'none';
    currentJobId = null;
    currentData = [];
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
        'Finalizing results...',
    ];
    let msgIndex = 0;

    clearInterval(progressInterval);
    progressInterval = setInterval(() => {
        width = Math.min(width + Math.random() * 12 + 3, 92);
        fill.style.width = width + '%';

        if (width > (msgIndex + 1) * (90 / messages.length) && msgIndex < messages.length - 1) {
            msgIndex++;
            updateLoadingText(messages[msgIndex]);
        }
    }, 600);
}

function updateLoadingText(text) {
    $('#loadingText').textContent = text;
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

    // Determine columns — exclude internal/very long fields
    const excludeFields = new Set(['_source_url', 'structured_data', 'images', 'lists', 'links', 'paragraphs', 'tables', 'extracted_items']);
    const allKeys = new Set();
    items.forEach(item => {
        Object.keys(item).forEach(k => {
            if (!excludeFields.has(k)) allKeys.add(k);
        });
    });
    const columns = Array.from(allKeys).slice(0, 10); // Max 10 columns for readability

    // Header
    const headerRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = formatColumnName(col);
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    // Rows (limit to 100 for performance)
    const displayItems = items.slice(0, 100);
    displayItems.forEach(item => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            let val = item[col];

            // Format value for display
            if (val === null || val === undefined) {
                td.textContent = '—';
                td.style.color = 'var(--text-muted)';
            } else if (typeof val === 'object') {
                td.textContent = JSON.stringify(val).slice(0, 100);
            } else {
                val = String(val);
                // Make URLs clickable
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
        note.textContent = `Showing 100 of ${items.length} records. Download the full dataset using the export buttons.`;
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

    stats.innerHTML = '';
    list.innerHTML = '';

    if (!validation || validation.total_records === undefined) {
        badge.className = 'validation-badge';
        badge.textContent = 'N/A';
        return;
    }

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
        <span><strong>${validation.total_records}</strong> records</span>
        <span><strong>${validation.total_fields}</strong> fields</span>
        <span><strong>${validation.error_count || 0}</strong> errors</span>
        <span><strong>${validation.warning_count || 0}</strong> warnings</span>
    `;

    // Issues
    const issues = validation.issues || [];
    if (issues.length === 0) {
        list.innerHTML = '<p style="color:var(--accent-green);font-size:0.9rem;">✓ All validation checks passed — data quality is good.</p>';
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
        // If no job ID, create a local download from current data
        if (currentData.length === 0) return;

        if (format === 'json') {
            downloadBlob(
                JSON.stringify(currentData, null, 2),
                'application/json',
                `mindrift_export.json`
            );
        } else {
            const csv = convertToCSV(currentData);
            downloadBlob(csv, 'text/csv', `mindrift_export.csv`);
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
    } catch (err) {
        // Fallback to local export
        if (format === 'json') {
            downloadBlob(
                JSON.stringify(currentData, null, 2),
                'application/json',
                `mindrift_export.json`
            );
        } else {
            const csv = convertToCSV(currentData);
            downloadBlob(csv, 'text/csv', `mindrift_export.csv`);
        }
    }
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
