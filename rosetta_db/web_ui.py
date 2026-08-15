"""
Simple Flask web UI for reviewing and editing translations.

Usage:
    python -m rosetta_db serve --port 8000 --lang es
"""

from flask import Flask, render_template_string, request, jsonify
from .database import Database

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Rosetta Translation Review</title>
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px;
            background: #1a1a2e; color: #eee;
        }
        .header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #333;
        }
        .header h1 { margin: 0; font-size: 1.5em; }
        .stats {
            display: flex; gap: 20px;
            background: #16213e; padding: 10px 15px; border-radius: 8px;
        }
        .stat { text-align: center; }
        .stat-value { font-size: 1.5em; font-weight: bold; color: #4ecca3; }
        .stat-label { font-size: 0.8em; color: #888; }
        .filters {
            display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;
        }
        .filters input, .filters select {
            padding: 8px 12px; border: 1px solid #333; border-radius: 4px;
            background: #16213e; color: #eee;
        }
        .filters input:focus, .filters select:focus { outline: none; border-color: #4ecca3; }
        .btn {
            padding: 8px 16px; border: none; border-radius: 4px;
            cursor: pointer; font-weight: 500;
        }
        .btn-primary { background: #4ecca3; color: #000; }
        .btn-primary:hover { background: #3db892; }
        .btn-secondary { background: #333; color: #eee; }
        .btn-secondary:hover { background: #444; }

        .string-list { display: flex; flex-direction: column; gap: 15px; }
        .string-card {
            background: #16213e; border-radius: 8px; padding: 15px;
            border-left: 4px solid #333;
        }
        .string-card.translated { border-left-color: #4ecca3; }
        .string-card.missing { border-left-color: #e94560; }
        .string-context {
            font-size: 0.8em; color: #888; margin-bottom: 10px;
            font-family: monospace; word-break: break-all;
        }
        .string-content { margin-bottom: 10px; }
        .string-label { font-weight: 500; color: #4ecca3; margin-bottom: 5px; }
        .string-text {
            background: #1a1a2e; padding: 10px; border-radius: 4px;
            white-space: pre-wrap; word-break: break-word; line-height: 1.5;
        }
        .string-text.en { color: #ccc; }
        .string-text.translation { color: #fff; }
        .translation-input {
            width: 100%; min-height: 80px; padding: 10px;
            background: #1a1a2e; border: 1px solid #333; border-radius: 4px;
            color: #fff; font-family: inherit; font-size: inherit;
            resize: vertical;
        }
        .translation-input:focus { outline: none; border-color: #4ecca3; }
        .string-actions {
            display: flex; gap: 10px; margin-top: 10px;
            justify-content: flex-end;
        }
        .pagination {
            display: flex; justify-content: center; gap: 10px;
            margin-top: 20px;
        }
        .page-info { padding: 8px 16px; color: #888; }

        .tabs { display: flex; gap: 5px; margin-bottom: 20px; }
        .tab {
            padding: 10px 20px; background: #16213e; border: none;
            color: #888; cursor: pointer; border-radius: 4px 4px 0 0;
        }
        .tab.active { background: #4ecca3; color: #000; }
        .tab:hover:not(.active) { background: #333; }

        .loading { text-align: center; padding: 40px; color: #888; }
        .message {
            padding: 10px 15px; border-radius: 4px; margin-bottom: 15px;
        }
        .message.success { background: #1e4d3c; color: #4ecca3; }
        .message.error { background: #4d1e2a; color: #e94560; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Rosetta Translation Review</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="stat-total">-</div>
                <div class="stat-label">Total</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-translated">-</div>
                <div class="stat-label">Translated</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-missing">-</div>
                <div class="stat-label">Missing</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-percent">-</div>
                <div class="stat-label">Progress</div>
            </div>
        </div>
    </div>

    <div class="tabs">
        <button class="tab active" data-filter="missing">Missing</button>
        <button class="tab" data-filter="translated">Translated</button>
        <button class="tab" data-filter="all">All</button>
    </div>

    <div class="filters">
        <input type="text" id="search" placeholder="Search..." style="flex: 1; min-width: 200px;">
        <input type="text" id="file-filter" placeholder="Filter by file..." style="width: 250px;">
        <select id="sort-by">
            <option value="file">Sort by file</option>
            <option value="length">Sort by length</option>
        </select>
    </div>

    <div id="message"></div>
    <div id="string-list" class="string-list">
        <div class="loading">Loading...</div>
    </div>

    <div class="pagination">
        <button class="btn btn-secondary" id="prev-page">Previous</button>
        <span class="page-info" id="page-info">Page 1</span>
        <button class="btn btn-secondary" id="next-page">Next</button>
    </div>

    <script>
        const VERSION = '{{ version }}';
        const LANG = '{{ lang }}';
        const PAGE_SIZE = 20;

        let currentPage = 1;
        let currentFilter = 'missing';
        let currentSearch = '';
        let currentFileFilter = '';
        let totalPages = 1;

        // Load stats
        async function loadStats() {
            const res = await fetch(`/api/stats?version=${VERSION}&lang=${LANG}`);
            const data = await res.json();
            document.getElementById('stat-total').textContent = data.total;
            document.getElementById('stat-translated').textContent = data.translated;
            document.getElementById('stat-missing').textContent = data.total - data.translated;
            document.getElementById('stat-percent').textContent = data.percent + '%';
        }

        // Load strings
        async function loadStrings() {
            const listEl = document.getElementById('string-list');
            listEl.innerHTML = '<div class="loading">Loading...</div>';

            const params = new URLSearchParams({
                version: VERSION,
                lang: LANG,
                filter: currentFilter,
                search: currentSearch,
                file: currentFileFilter,
                page: currentPage,
                per_page: PAGE_SIZE
            });

            const res = await fetch(`/api/strings?${params}`);
            const data = await res.json();

            totalPages = Math.ceil(data.total / PAGE_SIZE) || 1;
            document.getElementById('page-info').textContent =
                `Page ${currentPage} of ${totalPages} (${data.total} strings)`;

            if (data.strings.length === 0) {
                listEl.innerHTML = '<div class="loading">No strings found</div>';
                return;
            }

            listEl.innerHTML = data.strings.map(s => `
                <div class="string-card ${s.translated_text ? 'translated' : 'missing'}" data-id="${s.id}">
                    <div class="string-context">${escapeHtml(s.file_path)}::${escapeHtml(s.context)}</div>
                    <div class="string-content">
                        <div class="string-label">English:</div>
                        <div class="string-text en">${escapeHtml(s.en_text)}</div>
                    </div>
                    <div class="string-content">
                        <div class="string-label">${LANG.toUpperCase()}:</div>
                        <textarea class="translation-input"
                                  placeholder="Enter translation..."
                                  data-string-id="${s.id}">${escapeHtml(s.translated_text || '')}</textarea>
                    </div>
                    <div class="string-actions">
                        <button class="btn btn-primary save-btn" data-string-id="${s.id}">Save</button>
                    </div>
                </div>
            `).join('');

            // Add save handlers
            document.querySelectorAll('.save-btn').forEach(btn => {
                btn.addEventListener('click', () => saveTranslation(btn.dataset.stringId));
            });
        }

        // Save translation
        async function saveTranslation(stringId) {
            const textarea = document.querySelector(`textarea[data-string-id="${stringId}"]`);
            const text = textarea.value.trim();

            if (!text) {
                showMessage('Translation cannot be empty', 'error');
                return;
            }

            const res = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    string_id: stringId,
                    lang: LANG,
                    text: text
                })
            });

            const data = await res.json();
            if (data.success) {
                showMessage('Translation saved!', 'success');
                // Update card styling
                const card = document.querySelector(`[data-id="${stringId}"]`);
                card.classList.remove('missing');
                card.classList.add('translated');
                loadStats();
            } else {
                showMessage('Error saving: ' + data.error, 'error');
            }
        }

        function showMessage(text, type) {
            const el = document.getElementById('message');
            el.innerHTML = `<div class="message ${type}">${escapeHtml(text)}</div>`;
            setTimeout(() => el.innerHTML = '', 3000);
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }

        // Event handlers
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentFilter = tab.dataset.filter;
                currentPage = 1;
                loadStrings();
            });
        });

        document.getElementById('search').addEventListener('input', debounce(e => {
            currentSearch = e.target.value;
            currentPage = 1;
            loadStrings();
        }, 300));

        document.getElementById('file-filter').addEventListener('input', debounce(e => {
            currentFileFilter = e.target.value;
            currentPage = 1;
            loadStrings();
        }, 300));

        document.getElementById('prev-page').addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                loadStrings();
            }
        });

        document.getElementById('next-page').addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                loadStrings();
            }
        });

        function debounce(fn, ms) {
            let timer;
            return (...args) => {
                clearTimeout(timer);
                timer = setTimeout(() => fn(...args), ms);
            };
        }

        // Initial load
        loadStats();
        loadStrings();
    </script>
</body>
</html>
"""


def create_app(version: str, lang: str):
    """Create Flask app for translation review."""
    app = Flask(__name__)

    @app.route('/')
    def index():
        return render_template_string(HTML_TEMPLATE, version=version, lang=lang)

    @app.route('/api/stats')
    def api_stats():
        v = request.args.get('version', version)
        l = request.args.get('lang', lang)

        with Database() as db:
            strings = db.get_strings_for_compile(v, l)
            total = len(strings)
            translated = sum(1 for s in strings if s.get('translated_text'))
            percent = round(100 * translated / total) if total else 0

        return jsonify({
            'total': total,
            'translated': translated,
            'percent': percent
        })

    @app.route('/api/strings')
    def api_strings():
        v = request.args.get('version', version)
        l = request.args.get('lang', lang)
        filter_type = request.args.get('filter', 'all')
        search = request.args.get('search', '').lower()
        file_filter = request.args.get('file', '').lower()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        with Database() as db:
            strings = db.get_strings_for_compile(v, l)

        # Apply filters
        if filter_type == 'missing':
            strings = [s for s in strings if not s.get('translated_text')]
        elif filter_type == 'translated':
            strings = [s for s in strings if s.get('translated_text')]

        if search:
            strings = [s for s in strings if
                       search in s['en_text'].lower() or
                       search in (s.get('translated_text') or '').lower()]

        if file_filter:
            strings = [s for s in strings if file_filter in s['file_path'].lower()]

        # Pagination
        total = len(strings)
        start = (page - 1) * per_page
        end = start + per_page
        strings = strings[start:end]

        return jsonify({
            'strings': strings,
            'total': total,
            'page': page,
            'per_page': per_page
        })

    @app.route('/api/save', methods=['POST'])
    def api_save():
        data = request.json
        string_id = data.get('string_id')
        l = data.get('lang', lang)
        text = data.get('text', '').strip()

        if not string_id or not text:
            return jsonify({'success': False, 'error': 'Missing data'})

        try:
            with Database() as db:
                db.save_translation(string_id, l, text, status='reviewed')
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    return app
