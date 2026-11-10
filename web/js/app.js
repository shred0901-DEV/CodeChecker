// CodeChecker Frontend Logic

// グローバル状態
const state = {
    selectedPath: null,
    scanResults: null,
    activeFilter: 'ALL', // 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'
    searchQuery: '',
    selectedFindingId: null,
    explanationRequestId: 0,
    aiStatus: null,
    isScanning: false,
    isGeneratingAi: false,
    aiGeneratedFindings: {} // findingId -> providerName
};

// DOM要素
const elements = {
    dropZone: document.getElementById('drop-zone'),
    selectedPathText: document.getElementById('selected-path-text'),
    btnSelectFolder: document.getElementById('btn-select-folder'),
    btnSelectZip: document.getElementById('btn-select-zip'),
    btnStartScan: document.getElementById('btn-start-scan'),
    scanLockOverlay: document.getElementById('scan-lock-overlay'),
    progressContainer: document.getElementById('progress-container'),
    progressMessage: document.getElementById('progress-message'),
    progressPercent: document.getElementById('progress-percent'),
    progressBarFill: document.getElementById('progress-bar-fill'),
    countHigh: document.getElementById('count-high'),
    countMedium: document.getElementById('count-medium'),
    countLow: document.getElementById('count-low'),
    countTotal: document.getElementById('count-total'),
    filterCards: {
        all: document.getElementById('filter-card-all'),
        high: document.getElementById('filter-card-high'),
        medium: document.getElementById('filter-card-medium'),
        low: document.getElementById('filter-card-low')
    },
    inputSearch: document.getElementById('input-search'),
    filteredCount: document.getElementById('filtered-count'),
    findingsList: document.getElementById('findings-list'),
    detailPlaceholder: document.getElementById('detail-placeholder'),
    detailContent: document.getElementById('detail-content'),
    detailSeverityBadge: document.getElementById('detail-severity-badge'),
    detailCweBadge: document.getElementById('detail-cwe-badge'),
    detailSourceBadge: document.getElementById('detail-source-badge'),
    detailTitle: document.getElementById('detail-title'),
    detailFilePath: document.getElementById('detail-file-path'),
    detailLineNumber: document.getElementById('detail-line-number'),
    btnOpenDetailFile: document.getElementById('btn-open-detail-file'),
    btnOpenDetailFileIcon: document.getElementById('btn-open-detail-file-icon'),
    btnOpenDetailFileText: document.getElementById('btn-open-detail-file-text'),
    detailDescription: document.getElementById('detail-description'),
    detailCodeBlock: document.getElementById('detail-code-block'),
    aiLoading: document.getElementById('ai-loading'),
    aiLoadingText: document.getElementById('ai-loading-text'),
    aiLoadingSubtext: document.getElementById('ai-loading-subtext'),
    aiExplanationContainer: document.getElementById('ai-explanation-container'),
    activeAiBadge: document.getElementById('active-ai-badge'),
    activeAiLabel: document.getElementById('active-ai-label'),
    btnRequestAi: document.getElementById('btn-request-ai'),
    btnCopyAi: document.getElementById('btn-copy-ai'),
    aiProviderSelect: document.getElementById('ai-provider-select'),
    aiStatusIndicator: document.getElementById('ai-status-indicator'),
    toastContainer: document.getElementById('toast-container'),
    // 設定モーダル
    btnOpenSettings: document.getElementById('btn-open-settings'),
    btnCloseSettings: document.getElementById('btn-close-settings'),
    btnSaveSettings: document.getElementById('btn-save-settings'),
    settingsModal: document.getElementById('settings-modal'),
    settingsSavingOverlay: document.getElementById('settings-saving-overlay'),
    inputOllamaHost: document.getElementById('input-ollama-host'),
    selectOllamaModel: document.getElementById('select-ollama-model'),
    inputCliCodex: document.getElementById('input-cli-codex'),
    inputModelCodex: document.getElementById('input-model-codex'),
    detectedModelCodex: document.getElementById('detected-model-codex'),
    badgeStatusOllama: document.getElementById('badge-status-ollama'),
    badgeStatusCodex: document.getElementById('badge-status-codex'),
    // 公式AI API
    inputApiKeyChatgpt: document.getElementById('input-api-key-chatgpt'),
    inputModelChatgpt: document.getElementById('input-model-chatgpt'),
    badgeStatusChatgpt: document.getElementById('badge-status-chatgpt'),
    inputApiKeyClaude: document.getElementById('input-api-key-claude'),
    inputModelClaude: document.getElementById('input-model-claude'),
    badgeStatusClaude: document.getElementById('badge-status-claude'),
    inputApiKeyGemini: document.getElementById('input-api-key-gemini'),
    inputModelGemini: document.getElementById('input-model-gemini'),
    badgeStatusGemini: document.getElementById('badge-status-gemini'),
    // レポートモーダル
    btnExport: document.getElementById('btn-export'),
    exportModal: document.getElementById('export-modal'),
    btnCloseExport: document.getElementById('btn-close-export'),
    btnExportMarkdown: document.getElementById('btn-export-markdown'),
    btnExportHtml: document.getElementById('btn-export-html')
};

const providerNames = {
    'ollama': 'Ollama',
    'codex': 'Codex CLI',
    'chatgpt': 'ChatGPT API',
    'claude': 'Claude API',
    'gemini': 'Antigravity Agent API',
    'disabled': 'AI無効'
};

function getApi() {
    return window.pywebview ? window.pywebview.api : null;
}

window.addEventListener('pywebviewready', async () => {
    console.log("PyWebView Ready");
    await initAiStatus();
});

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    updateFilterCardStyles();
});

window.onScanProgress = (message, percent) => {
    elements.progressContainer.classList.remove('hidden');
    elements.progressMessage.textContent = message;
    elements.progressPercent.textContent = `${percent}%`;
    elements.progressBarFill.style.width = `${percent}%`;
};

// AIステータスのロード
async function initAiStatus() {
    const api = getApi();
    if (!api) return;

    try {
        const status = await api.get_ai_status();
        state.aiStatus = status;

        elements.aiProviderSelect.value = status.active_provider;
        elements.inputOllamaHost.value = status.ollama.host;

        if (status.clis && status.clis.codex) {
            elements.inputCliCodex.value = status.clis.codex.command;
            elements.inputModelCodex.value = status.clis.codex.selected_model || "default";
            if (elements.detectedModelCodex) {
                elements.detectedModelCodex.textContent = status.clis.codex.detected_model 
                    ? `CLI設定モデル: ${status.clis.codex.detected_model}` 
                    : '※設定モデル未検出 (default使用)';
            }
            updateCliBadge(elements.badgeStatusCodex, status.clis.codex?.available);
        }
        updateCliBadge(elements.badgeStatusOllama, status.ollama.available);

        elements.selectOllamaModel.innerHTML = '';
        if (status.ollama.models && status.ollama.models.length > 0) {
            status.ollama.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                if (m === status.ollama.selected_model) opt.selected = true;
                elements.selectOllamaModel.appendChild(opt);
            });
        } else {
            const opt = document.createElement('option');
            opt.value = status.ollama.selected_model || "gemma4:12b-it-q4_K_M";
            opt.textContent = status.ollama.selected_model || "gemma4:12b-it-q4_K_M";
            elements.selectOllamaModel.appendChild(opt);
        }

        // 公式APIステータス反映
        if (status.apis) {
            if (status.apis.chatgpt) {
                elements.inputModelChatgpt.value = status.apis.chatgpt.selected_model || "gpt-4o-mini";
                updateApiBadge(elements.badgeStatusChatgpt, status.apis.chatgpt.has_key, status.apis.chatgpt.masked_key);
                if (status.apis.chatgpt.has_key) {
                    elements.inputApiKeyChatgpt.placeholder = `設定済み (${status.apis.chatgpt.masked_key})`;
                }
            }
            if (status.apis.claude) {
                elements.inputModelClaude.value = status.apis.claude.selected_model || "claude-3-7-sonnet-20250219";
                updateApiBadge(elements.badgeStatusClaude, status.apis.claude.has_key, status.apis.claude.masked_key);
                if (status.apis.claude.has_key) {
                    elements.inputApiKeyClaude.placeholder = `設定済み (${status.apis.claude.masked_key})`;
                }
            }
            if (status.apis.gemini) {
                elements.inputModelGemini.value = status.apis.gemini.selected_model || "gemini-3.8-flash";
                updateApiBadge(elements.badgeStatusGemini, status.apis.gemini.has_key, status.apis.gemini.masked_key);
                if (status.apis.gemini.has_key) {
                    elements.inputApiKeyGemini.placeholder = `設定済み (${status.apis.gemini.masked_key})`;
                }
            }
        }

        updateAiIndicator();
    } catch (e) {
        console.error("AIステータス取得失敗:", e);
    }
}

function updateCliBadge(badgeEl, isAvailable) {
    if (!badgeEl) return;
    if (isAvailable) {
        badgeEl.textContent = '検出済み';
        badgeEl.className = 'px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
    } else {
        badgeEl.textContent = '未検出';
        badgeEl.className = 'px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-500';
    }
}

function updateApiBadge(badgeEl, hasKey, maskedKey) {
    if (!badgeEl) return;
    if (hasKey) {
        badgeEl.textContent = '設定済み';
        badgeEl.className = 'px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        badgeEl.title = maskedKey ? `登録中: ${maskedKey}` : '設定済み';
    } else {
        badgeEl.textContent = '未設定';
        badgeEl.className = 'px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-500';
        badgeEl.title = 'APIキーが未設定です';
    }
}

function updateAiIndicator() {
    if (!state.aiStatus) return;
    const provider = elements.aiProviderSelect.value;
    const ind = elements.aiStatusIndicator;

    // ※ elements.activeAiLabel は現在表示中の解説のプロバイダを示すため、
    // プロバイダ選択ドロップダウンの変更では書き換えず、解説の取得完了時にのみ更新します。

    if (provider === 'disabled') {
        ind.className = 'w-2 h-2 rounded-full bg-slate-500';
        ind.title = 'AI機能は無効';
        return;
    }

    let isAvailable = false;
    let modelName = '';
    let notAvailableMsg = '未検出 (設定をご確認ください)';

    if (provider === 'ollama') {
        isAvailable = state.aiStatus.ollama?.available;
        modelName = state.aiStatus.ollama?.selected_model || '';
        notAvailableMsg = 'サーバー未検出 (Ollama起動を確認してください)';
    } else if (state.aiStatus.clis && state.aiStatus.clis[provider]) {
        const cliInfo = state.aiStatus.clis[provider];
        isAvailable = cliInfo.available;
        modelName = (cliInfo.selected_model && cliInfo.selected_model !== 'default')
            ? cliInfo.selected_model
            : (cliInfo.detected_model || 'default');
        notAvailableMsg = 'コマンド未検出 (設定をご確認ください)';
    } else if (state.aiStatus.apis && state.aiStatus.apis[provider]) {
        const apiInfo = state.aiStatus.apis[provider];
        isAvailable = apiInfo.available;
        modelName = apiInfo.selected_model || '';
        notAvailableMsg = 'APIキー未設定 (設定画面で入力してください)';
    }

    const pLabel = providerNames[provider] || provider;
    const mLabel = modelName ? ` (${modelName})` : '';

    if (isAvailable) {
        ind.className = 'w-2 h-2 rounded-full bg-emerald-500';
        ind.title = `${pLabel} 利用可能${mLabel}`;
    } else {
        ind.className = 'w-2 h-2 rounded-full bg-amber-500';
        ind.title = `${pLabel} ${notAvailableMsg}`;
    }
}

// イベントリスナー設定
function setupEventListeners() {
    elements.btnSelectFolder.addEventListener('click', async (e) => {
        e.stopPropagation();
        const api = getApi();
        if (api) {
            const folder = await api.select_folder();
            if (folder) setSelectedPath(folder);
        }
    });

    elements.btnSelectZip.addEventListener('click', async (e) => {
        e.stopPropagation();
        const api = getApi();
        if (api) {
            const file = await api.select_file();
            if (file) setSelectedPath(file);
        }
    });

    elements.dropZone.addEventListener('click', async () => {
        const api = getApi();
        if (api) {
            const folder = await api.select_folder();
            if (folder) setSelectedPath(folder);
        }
    });

    elements.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.dropZone.classList.add('drop-zone-active');
    });

    elements.dropZone.addEventListener('dragleave', () => {
        elements.dropZone.classList.remove('drop-zone-active');
    });

    elements.dropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        elements.dropZone.classList.remove('drop-zone-active');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            let path = file.path;

            // WebView2 等で path が直接渡らない場合のパス解決
            if (!path) {
                const api = getApi();
                if (api && api.resolve_dropped_path) {
                    try {
                        for (let i = 0; i < 5; i++) {
                            const resolved = await api.resolve_dropped_path(file.name);
                            if (resolved) {
                                path = resolved;
                                break;
                            }
                            await new Promise(r => setTimeout(r, 60));
                        }
                    } catch (err) {
                        console.error("resolve_dropped_path error:", err);
                    }
                }
            }

            if (!path) {
                path = file.name;
            }
            setSelectedPath(path);
        }
    });

    elements.btnStartScan.addEventListener('click', startScan);

    elements.filterCards.all.addEventListener('click', () => setFilter('ALL'));
    elements.filterCards.high.addEventListener('click', () => setFilter('HIGH'));
    elements.filterCards.medium.addEventListener('click', () => setFilter('MEDIUM'));
    elements.filterCards.low.addEventListener('click', () => setFilter('LOW'));

    elements.inputSearch.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.toLowerCase();
        renderFindingsList();
    });

    // AIプロバイダ即時変更 (自動再生成は行わず、ユーザーが再生成ボタンを押したときのみ動作)
    elements.aiProviderSelect.addEventListener('change', async (e) => {
        const api = getApi();
        if (api) {
            updateAiIndicator();
            await api.update_ai_settings({ active_provider: e.target.value });
            await initAiStatus();
            // ※誤操作等に配慮し、自動再生成は行いません。
            // ユーザーが「AI解説を再生成」ボタンを押下した時のみ明示的に実行されます。
        }
    });

    elements.btnRequestAi.addEventListener('click', () => {
        if (state.selectedFindingId) {
            fetchAiExplanation(state.selectedFindingId, true);
        }
    });

    elements.btnCopyAi.addEventListener('click', () => {
        const text = elements.aiExplanationContainer.innerText;
        navigator.clipboard.writeText(text);
        elements.btnCopyAi.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i><span class="text-emerald-400">コピー完了</span>';
        setTimeout(() => {
            elements.btnCopyAi.innerHTML = '<i class="fa-regular fa-copy"></i><span>コピー</span>';
        }, 2000);
    });

    // ★ヘッダーの「エディタで開く」/「ファイルの場所を開く」ボタン (UX-01)
    elements.btnOpenDetailFile.addEventListener('click', async () => {
        if (!state.selectedFindingId || !state.scanResults) return;
        const finding = state.scanResults.findings.find(f => f.id === state.selectedFindingId);
        if (finding) {
            const isBinary = finding.source === 'pe-binary' ||
                             (finding.file && (finding.file.toLowerCase().endsWith('.exe') ||
                                               finding.file.toLowerCase().endsWith('.dll') ||
                                               finding.file.toLowerCase().endsWith('.sys') ||
                                               finding.file.toLowerCase().endsWith('.ocx')));
            if (isBinary) {
                await handleOpenFileLocation(finding.full_path || finding.file);
            } else {
                await handleOpenFile(finding.full_path || finding.file, finding.line);
            }
        }
    });

    // ★AI解説内のリンククリックハンドラ (Webリンクはブラウザ、ファイルリンクはエディタ)
    elements.aiExplanationContainer.addEventListener('click', async (e) => {
        const link = e.target.closest('a');
        if (!link) return;
        e.preventDefault();

        const href = link.getAttribute('href') || '';
        const api = getApi();

        if (href.startsWith('http://') || href.startsWith('https://')) {
            // Webページリンク -> 既定ブラウザで起動
            if (api) {
                api.open_external_url(href);
            } else {
                window.open(href, '_blank');
            }
        } else {
            // ソースコードファイルリンク -> 既定エディタ(VS Code等)で起動
            await handleOpenFile(href);
        }
    });

    // 設定モーダル開閉
    elements.btnOpenSettings.addEventListener('click', () => elements.settingsModal.classList.remove('hidden'));
    elements.btnCloseSettings.addEventListener('click', () => elements.settingsModal.classList.add('hidden'));
    elements.btnSaveSettings.addEventListener('click', saveSettings);

    document.querySelectorAll('.btn-test-cli').forEach(btn => {
        btn.addEventListener('click', async () => {
            const cliId = btn.getAttribute('data-cli');
            const api = getApi();
            if (!api) return;

            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>テスト中...';

            try {
                await saveSettingsQuiet();
                const res = await api.test_cli(cliId);
                alert(`[${cliId.toUpperCase()} 接続テスト]\n${res.message}`);
            } catch (err) {
                alert(`テスト実行エラー: ${err}`);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-plug-circle-bolt mr-1"></i>テスト実行';
                await initAiStatus();
            }
        });
    });

    document.querySelectorAll('.btn-test-api').forEach(btn => {
        btn.addEventListener('click', async () => {
            const apiId = btn.getAttribute('data-api');
            const api = getApi();
            if (!api) return;

            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>テスト中...';

            try {
                await saveSettingsQuiet();
                const res = await api.test_api(apiId);
                const pLabel = providerNames[apiId] || apiId;
                alert(`[${pLabel} 接続テスト]\n${res.message}`);
            } catch (err) {
                alert(`テスト実行エラー: ${err}`);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-plug-circle-bolt mr-1"></i>テスト実行';
                await initAiStatus();
            }
        });
    });

    elements.btnExport.addEventListener('click', () => elements.exportModal.classList.remove('hidden'));
    elements.btnCloseExport.addEventListener('click', () => elements.exportModal.classList.add('hidden'));
    elements.btnExportMarkdown.addEventListener('click', () => exportReport('markdown'));
    elements.btnExportHtml.addEventListener('click', () => exportReport('html'));
}

// ファイルをエディタで開く共通ハンドラ (ZIP一時展開時のトースト通知付き)
async function handleOpenFile(targetRef, lineNum = null) {
    const api = getApi();
    if (!api) return;

    const fullRef = lineNum ? `${targetRef}#L${lineNum}` : targetRef;
    const res = await api.open_source_file(fullRef);

    if (res.success) {
        if (res.is_temp) {
            showToast(
                "⚠️ 一時展開ファイルを開きました",
                `${res.file_name} を開きました。\n※ZIPから展開された一時ファイルのため、編集・保存しても元のZIPファイルには反映されません。`,
                "warning",
                7000
            );
        } else {
            showToast(
                "📄 ファイルを開きました",
                `${res.file_name} を ${res.editor} で開きました。`,
                "info",
                3000
            );
        }
    } else {
        showToast("ファイルを開けませんでした", res.error || "パスが無効です", "error", 4000);
    }
}

// ファイルの場所をOSファイラーで開くハンドラ (UX-01)
async function handleOpenFileLocation(targetRef) {
    const api = getApi();
    if (!api) return;

    try {
        const res = await api.open_file_location(targetRef);
        if (res.success) {
            showToast(
                "📁 ファイルの場所を開きました",
                `${res.file_name} をエクスプローラーで選択表示しました。`,
                "info",
                4000
            );
        } else {
            showToast("ファイラーを開けませんでした", res.error || "パスが無効です", "error", 4000);
        }
    } catch (e) {
        showToast("エラー", `ファイラー起動時例外: ${e}`, "error", 4000);
    }
}

// ファイル拡張子に応じた Prism 言語クラスの判定 (UX-02)
function getLanguageClassByFilename(filename, isBinary = false) {
    if (isBinary) return 'language-none';
    if (!filename) return 'language-clike';
    const parts = filename.split('.');
    if (parts.length <= 1) return 'language-clike';
    const ext = parts.pop().toLowerCase();
    const map = {
        'py': 'language-python',
        'pyw': 'language-python',
        'js': 'language-javascript',
        'jsx': 'language-javascript',
        'mjs': 'language-javascript',
        'cjs': 'language-javascript',
        'ts': 'language-typescript',
        'tsx': 'language-typescript',
        'c': 'language-c',
        'h': 'language-c',
        'cpp': 'language-cpp',
        'cc': 'language-cpp',
        'cxx': 'language-cpp',
        'hpp': 'language-cpp',
        'hxx': 'language-cpp',
        'cs': 'language-csharp',
        'java': 'language-java',
        'go': 'language-go',
        'rs': 'language-rust',
        'php': 'language-php',
        'phtml': 'language-php',
        'rb': 'language-ruby',
        'sh': 'language-bash',
        'bash': 'language-bash',
        'zsh': 'language-bash',
        'ps1': 'language-powershell',
        'bat': 'language-batch',
        'cmd': 'language-batch',
        'sql': 'language-sql',
        'html': 'language-html',
        'htm': 'language-html',
        'xml': 'language-xml',
        'json': 'language-json',
        'yaml': 'language-yaml',
        'yml': 'language-yaml',
    };
    return map[ext] || 'language-clike';
}

// モダンなトースト通知の表示
function showToast(title, message, type = "info", duration = 4000) {
    const container = elements.toastContainer;
    if (!container) return;

    const toast = document.createElement('div');
    let borderClass = "border-slate-700 bg-slate-900";
    let iconClass = "fa-circle-info text-sky-400";

    if (type === "warning") {
        borderClass = "border-amber-500/50 bg-slate-900 shadow-amber-500/10";
        iconClass = "fa-triangle-exclamation text-amber-400";
    } else if (type === "error") {
        borderClass = "border-red-500/50 bg-slate-900 shadow-red-500/10";
        iconClass = "fa-circle-xmark text-red-400";
    }

    toast.className = `pointer-events-auto w-80 p-3.5 rounded-xl border shadow-xl flex items-start gap-3 animate-toast ${borderClass} transition`;
    toast.innerHTML = `
        <div class="mt-0.5 text-base shrink-0"><i class="fa-solid ${iconClass}"></i></div>
        <div class="flex-1 text-xs">
            <div class="font-bold text-slate-200 mb-0.5">${escapeHtml(title)}</div>
            <div class="text-slate-400 leading-relaxed whitespace-pre-line text-[11px]">${escapeHtml(message)}</div>
        </div>
        <button class="text-slate-500 hover:text-slate-300 text-xs shrink-0"><i class="fa-solid fa-xmark"></i></button>
    `;

    toast.querySelector('button').addEventListener('click', () => {
        toast.remove();
    });

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function setSelectedPath(path) {
    state.selectedPath = path;
    elements.selectedPathText.textContent = path;
    elements.selectedPathText.title = path;
    elements.selectedPathText.className = "text-xs font-mono text-indigo-300 font-semibold truncate";
    elements.btnStartScan.disabled = false;
}
window.setSelectedPath = setSelectedPath;

// スキャン開始
async function startScan() {
    if (!state.selectedPath || state.isScanning) return;
    const api = getApi();
    if (!api) return;

    state.isScanning = true;
    state.aiGeneratedFindings = {};
    elements.btnStartScan.disabled = true;

    // ★危険度ボタン以下の領域をぼかしオーバーレイでロック
    if (elements.scanLockOverlay) {
        elements.scanLockOverlay.classList.remove('hidden');
    }

    elements.progressContainer.classList.remove('hidden');
    elements.progressMessage.textContent = '初期化中...';
    elements.progressBarFill.style.width = '5%';

    try {
        const results = await api.start_scan(state.selectedPath);
        if (results.error) {
            alert(results.error);
            return;
        }

        state.scanResults = results;
        updateSummary(results.summary);
        renderFindingsList();

        if (results.findings && results.findings.length > 0) {
            selectFinding(results.findings[0].id);
        } else {
            resetDetailView();
        }
    } catch (e) {
        console.error("スキャン実行時エラー:", e);
        alert("スキャン中に予期せぬエラーが発生しました: " + e);
    } finally {
        state.isScanning = false;
        elements.btnStartScan.disabled = false;
        // ★ロック解除
        if (elements.scanLockOverlay) {
            elements.scanLockOverlay.classList.add('hidden');
        }
        setTimeout(() => {
            elements.progressContainer.classList.add('hidden');
        }, 1500);
    }
}

function updateSummary(summary) {
    if (!summary) return;
    elements.countHigh.textContent = summary.high || 0;
    elements.countMedium.textContent = summary.medium || 0;
    elements.countLow.textContent = summary.low || 0;
    elements.countTotal.textContent = summary.total || 0;
}

function setFilter(filterType) {
    state.activeFilter = filterType;
    updateFilterCardStyles();
    renderFindingsList();
}

function updateFilterCardStyles() {
    const cards = [
        { el: elements.filterCards.all, type: 'ALL', activeClass: 'ring-2 ring-inset ring-indigo-500 bg-indigo-500/10' },
        { el: elements.filterCards.high, type: 'HIGH', activeClass: 'ring-2 ring-inset ring-red-500 bg-red-500/10' },
        { el: elements.filterCards.medium, type: 'MEDIUM', activeClass: 'ring-2 ring-inset ring-amber-500 bg-amber-500/10' },
        { el: elements.filterCards.low, type: 'LOW', activeClass: 'ring-2 ring-inset ring-emerald-500 bg-emerald-500/10' }
    ];

    const removeClasses = [
        'ring-2', 'ring-inset',
        'ring-indigo-500', 'ring-red-500', 'ring-amber-500', 'ring-emerald-500',
        'bg-indigo-500/10', 'bg-red-500/10', 'bg-amber-500/10', 'bg-emerald-500/10'
    ];

    cards.forEach(c => {
        c.el.classList.remove(...removeClasses);
        if (state.activeFilter === c.type) {
            c.activeClass.split(' ').forEach(cls => c.el.classList.add(cls));
        }
    });
}

function renderFindingsList() {
    const list = elements.findingsList;
    const prevScrollTop = list.scrollTop;
    list.innerHTML = '';

    if (!state.scanResults || !state.scanResults.findings || state.scanResults.findings.length === 0) {
        list.innerHTML = `
            <div class="h-full flex flex-col items-center justify-center text-slate-500 p-6 text-center">
                <i class="fa-solid fa-shield-check text-3xl mb-3 text-emerald-500"></i>
                <p class="text-xs font-medium text-slate-300">脆弱性は検出されませんでした</p>
                <p class="text-[11px] text-slate-500 mt-1">スキャン対象コードは安全です。</p>
            </div>
        `;
        elements.filteredCount.textContent = '0 件';
        return;
    }

    let findings = state.scanResults.findings;
    if (state.activeFilter !== 'ALL') {
        findings = findings.filter(f => f.severity === state.activeFilter);
    }
    if (state.searchQuery) {
        findings = findings.filter(f => 
            f.title.toLowerCase().includes(state.searchQuery) ||
            f.file.toLowerCase().includes(state.searchQuery) ||
            f.cwe.toLowerCase().includes(state.searchQuery) ||
            f.description.toLowerCase().includes(state.searchQuery)
        );
    }

    elements.filteredCount.textContent = `${findings.length} 件`;

    if (findings.length === 0) {
        list.innerHTML = `
            <div class="h-32 flex flex-col items-center justify-center text-slate-500 p-4 text-center">
                <p class="text-xs">条件に一致する指摘はありません</p>
            </div>
        `;
        return;
    }

    findings.forEach(f => {
        const item = document.createElement('div');
        const isSelected = f.id === state.selectedFindingId;
        
        let sevBg = 'bg-slate-800 text-slate-400';
        let barColor = 'bg-slate-600';
        if (f.severity === 'HIGH') {
            sevBg = 'bg-red-500/20 text-red-400 border border-red-500/30';
            barColor = 'bg-red-500';
        } else if (f.severity === 'MEDIUM') {
            sevBg = 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
            barColor = 'bg-amber-500';
        } else if (f.severity === 'LOW') {
            sevBg = 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
            barColor = 'bg-emerald-500';
        }

        // 選択中ハイライト: インディゴ色のリング & 背景
        // 未選択: 薄いボーダー & ホバー時の微小変化
        const selectionClass = isSelected 
            ? 'bg-indigo-600/15 ring-2 ring-indigo-500 border border-indigo-500/40 shadow-md shadow-indigo-500/10' 
            : 'bg-slate-950/40 border border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700/80';

        item.className = `relative pl-4 pr-3 py-3 rounded-lg cursor-pointer transition-all flex flex-col gap-1.5 overflow-hidden ${selectionClass}`;
        
        // AI生成ステータスバッジ (生成済みの場合のみ表示)
        let generatedBadgeHtml = '';
        if (state.aiGeneratedFindings && state.aiGeneratedFindings[f.id]) {
            const pName = state.aiGeneratedFindings[f.id];
            generatedBadgeHtml = `
                <div class="mt-0.5 flex items-center gap-1.5 text-[10px] text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 w-fit">
                    <i class="fa-solid fa-robot text-[9px] text-indigo-400"></i>
                    <span>${escapeHtml(pName)}によって生成済み</span>
                </div>
            `;
        }

        const isBinary = f.source === 'pe-binary' || f.file.toLowerCase().endsWith('.exe') || f.file.toLowerCase().endsWith('.dll');
        const fileIcon = isBinary ? 'fa-solid fa-cube text-indigo-400' : 'fa-regular fa-file text-slate-500';
        const lineLabel = isBinary ? 'Binary' : `L${f.line}`;

        item.innerHTML = `
            <!-- 危険度カラーバー (左端) -->
            <div class="absolute left-0 top-0 bottom-0 w-1.5 ${barColor}"></div>

            <div class="flex items-center justify-between gap-2">
                <span class="text-xs font-bold text-slate-200 truncate">${escapeHtml(f.title)}</span>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${sevBg}">${f.severity}</span>
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span class="truncate flex items-center gap-1.5">
                    <i class="${fileIcon}"></i>
                    ${escapeHtml(f.file)}
                </span>
                <span class="text-slate-500 shrink-0">${lineLabel}</span>
            </div>
            ${generatedBadgeHtml}
        `;

        item.addEventListener('click', () => selectFinding(f.id));
        list.appendChild(item);
    });

    list.scrollTop = prevScrollTop;
}

async function selectFinding(findingId) {
    state.selectedFindingId = findingId;
    renderFindingsList();

    const finding = state.scanResults.findings.find(f => f.id === findingId);
    if (!finding) return;

    elements.detailPlaceholder.classList.add('hidden');
    elements.detailContent.classList.remove('hidden');

    elements.detailTitle.textContent = finding.title;
    elements.detailCweBadge.textContent = finding.cwe;
    elements.detailSourceBadge.textContent = finding.source;
    const isBinary = finding.source === 'pe-binary' ||
                     (finding.file && (finding.file.toLowerCase().endsWith('.exe') ||
                                       finding.file.toLowerCase().endsWith('.dll') ||
                                       finding.file.toLowerCase().endsWith('.sys') ||
                                       finding.file.toLowerCase().endsWith('.ocx')));

    elements.detailFilePath.textContent = finding.file;
    elements.detailLineNumber.textContent = isBinary ? 'Binary' : `L${finding.line}`;
    elements.detailDescription.textContent = finding.description;

    // バイナリ指摘時の「ファイルの場所を開く」ボタン切替 (UX-01)
    if (isBinary) {
        if (elements.btnOpenDetailFileIcon) elements.btnOpenDetailFileIcon.className = 'fa-regular fa-folder-open';
        if (elements.btnOpenDetailFileText) elements.btnOpenDetailFileText.textContent = 'ファイルの場所を開く';
        elements.btnOpenDetailFile.title = 'このファイルの場所をエクスプローラーで開く';
    } else {
        if (elements.btnOpenDetailFileIcon) elements.btnOpenDetailFileIcon.className = 'fa-regular fa-pen-to-square';
        if (elements.btnOpenDetailFileText) elements.btnOpenDetailFileText.textContent = 'エディタで開く';
        elements.btnOpenDetailFile.title = 'このファイルをエディタで開く';
    }

    elements.detailSeverityBadge.textContent = finding.severity;
    if (finding.severity === 'HIGH') {
        elements.detailSeverityBadge.className = 'px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-red-500/20 text-red-400 border border-red-500/40';
    } else if (finding.severity === 'MEDIUM') {
        elements.detailSeverityBadge.className = 'px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/40';
    } else {
        elements.detailSeverityBadge.className = 'px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/40';
    }

    // コードプレビューのシンタックスハイライト言語自動切替 (UX-02)
    const langClass = getLanguageClassByFilename(finding.file, isBinary);
    elements.detailCodeBlock.className = langClass;
    elements.detailCodeBlock.textContent = finding.code || '// コードが見つかりませんでした';
    try {
        Prism.highlightElement(elements.detailCodeBlock);
    } catch (prismErr) {
        console.warn('Prism syntax highlighting failed:', prismErr);
    }

    fetchAiExplanation(findingId);
}

// AI解説の取得・生成 (非同期競合防止 & 厳密な検証ガード付き)
async function fetchAiExplanation(findingId, force = false) {
    const api = getApi();
    if (!api || !findingId) return;

    // 推論処理中はバッジを非表示にする (完了して解説が表示されるまで見せない)
    if (elements.activeAiBadge) {
        elements.activeAiBadge.classList.add('hidden');
    }

    // 再生成時(force=true)は推論中になるため、一覧の生成済み表示もバッジと同じタイミングで非表示にする
    if (force && state.aiGeneratedFindings[findingId]) {
        delete state.aiGeneratedFindings[findingId];
        renderFindingsList();
    }

    const currentProvider = elements.aiProviderSelect.value;
    if (currentProvider === 'disabled') {
        elements.aiLoading.classList.add('hidden');
        elements.aiExplanationContainer.classList.remove('hidden');
        elements.aiExplanationContainer.innerHTML = '<p class="text-slate-500">AI機能は現在オフです。</p>';
        return;
    }

    // 新しい非同期リクエスト番号を採番 (競合防止)
    const reqId = ++state.explanationRequestId;
    state.isGeneratingAi = true;

    // 処理中表示に切り替え (表示準備が整うまで確実に処理中であることを明示)
    elements.aiLoading.classList.remove('hidden');
    elements.aiExplanationContainer.classList.add('hidden');

    const pName = providerNames[currentProvider] || currentProvider;
    elements.aiLoadingText.textContent = `${pName} が脆弱性を分析中...`;
    elements.aiLoadingSubtext.textContent = '推論を実行中 (処理中)...';

    try {
        // ★現在UIで選択されているプロバイダ (currentProvider) と再生成フラグ (force) を確実に渡す
        const res = await api.explain_finding(findingId, currentProvider, force);

        // ★厳密な検証ガード:
        // リクエスト完了時に「現在選択されている指摘ID」かつ「最新のリクエストID」である場合のみUIに反映
        if (reqId !== state.explanationRequestId || state.selectedFindingId !== findingId) {
            // 他の指摘や別のリクエストが先行しているため、古い結果は画面に反映せず破棄
            return;
        }

        // 表示可能な状態になってからローディングを解除してコンテンツを表示
        elements.aiLoading.classList.add('hidden');
        elements.aiExplanationContainer.classList.remove('hidden');

        if (res.error) {
            elements.aiExplanationContainer.innerHTML = `<p class="text-red-400">${escapeHtml(res.error)}</p>`;
            if (elements.activeAiBadge) elements.activeAiBadge.classList.add('hidden');
            if (state.aiGeneratedFindings[findingId]) {
                delete state.aiGeneratedFindings[findingId];
                renderFindingsList();
            }
        } else {
            // Marked.js でパースし安全にサニタイズ (XSS防止)
            const rawHtml = marked.parse(res.explanation);
            elements.aiExplanationContainer.innerHTML = sanitizeHtml(rawHtml);
            
            // ★リンクの精査とデザイン差別化 (Webリンク vs ファイルリンク)
            enhanceExplanationLinks(elements.aiExplanationContainer);

            // 解説・修正提案の表示完了時にバッジを更新・表示
            const usedPName = providerNames[res.provider] || res.provider;
            if (elements.activeAiLabel) {
                elements.activeAiLabel.textContent = `${usedPName} (${res.model})`;
            }
            if (elements.activeAiBadge) {
                elements.activeAiBadge.classList.remove('hidden');
            }

            // 脆弱性一覧リストの該当項目にも「〇〇によって生成済み」を表示 (バッジと同じタイミングで表示)
            state.aiGeneratedFindings[findingId] = usedPName;
            renderFindingsList();
        }
    } catch (e) {
        if (reqId !== state.explanationRequestId || state.selectedFindingId !== findingId) {
            return;
        }
        elements.aiLoading.classList.add('hidden');
        elements.aiExplanationContainer.classList.remove('hidden');
        elements.aiExplanationContainer.innerHTML = `<p class="text-red-400">AI解説の取得中にエラーが発生しました: ${escapeHtml(String(e))}</p>`;
        if (elements.activeAiBadge) elements.activeAiBadge.classList.add('hidden');
        if (state.aiGeneratedFindings[findingId]) {
            delete state.aiGeneratedFindings[findingId];
            renderFindingsList();
        }
    } finally {
        if (reqId === state.explanationRequestId) {
            state.isGeneratingAi = false;
        }
    }
}

// AI解説内の <a> タグを精査してスタイルクラス・タイトルを付与
function enhanceExplanationLinks(container) {
    const links = container.querySelectorAll('a');
    links.forEach(a => {
        const href = a.getAttribute('href') || '';
        if (href.startsWith('http://') || href.startsWith('https://')) {
            a.classList.add('link-web');
            a.setAttribute('title', 'ブラウザでWebページを開く');
        } else {
            a.classList.add('link-file');
            a.setAttribute('title', 'クリックして既定エディタ(VS Code等)で開く');
        }
    });
}

function resetDetailView() {
    state.selectedFindingId = null;
    state.explanationRequestId++;
    elements.detailPlaceholder.classList.remove('hidden');
    elements.detailContent.classList.add('hidden');
    elements.aiLoading.classList.add('hidden');
    elements.aiExplanationContainer.classList.add('hidden');
    if (elements.activeAiBadge) elements.activeAiBadge.classList.add('hidden');
    if (elements.activeAiLabel) elements.activeAiLabel.textContent = '';
}

// 画面ロック付き設定保存
async function saveSettings() {
    const overlay = elements.settingsSavingOverlay;
    const btn = elements.btnSaveSettings;

    if (overlay) overlay.classList.remove('hidden');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i><span>保存中...</span>';
    }

    try {
        await saveSettingsQuiet();
    } catch (err) {
        alert("設定の保存に失敗しました: " + err);
    } finally {
        if (overlay) overlay.classList.add('hidden');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span>保存して閉じる</span>';
        }
        elements.settingsModal.classList.add('hidden');
    }
}

async function saveSettingsQuiet() {
    const api = getApi();
    if (!api) return;

    const payload = {
        active_provider: elements.aiProviderSelect.value,
        ollama: {
            host: elements.inputOllamaHost.value,
            selected_model: elements.selectOllamaModel.value
        },
        clis: {
            codex: {
                command: elements.inputCliCodex.value,
                selected_model: elements.inputModelCodex.value
            }
        },
        apis: {
            chatgpt: {
                api_key: elements.inputApiKeyChatgpt.value.trim(),
                selected_model: elements.inputModelChatgpt.value.trim()
            },
            claude: {
                api_key: elements.inputApiKeyClaude.value.trim(),
                selected_model: elements.inputModelClaude.value.trim()
            },
            gemini: {
                api_key: elements.inputApiKeyGemini.value.trim(),
                selected_model: elements.inputModelGemini.value.trim()
            }
        }
    };

    const updated = await api.update_ai_settings(payload);
    state.aiStatus = updated;
    
    // 入力されたAPIキー欄をクリアしてプレースホルダーを更新
    if (elements.inputApiKeyChatgpt.value) elements.inputApiKeyChatgpt.value = '';
    if (elements.inputApiKeyClaude.value) elements.inputApiKeyClaude.value = '';
    if (elements.inputApiKeyGemini.value) elements.inputApiKeyGemini.value = '';

    await initAiStatus();
}

async function exportReport(format) {
    const api = getApi();
    if (!api) return;

    elements.exportModal.classList.add('hidden');
    const res = await api.export_report(format);
    if (res.status === 'success') {
        alert(`レポートを保存しました:\n${res.saved_path}`);
    } else if (res.error) {
        alert(`レポート保存エラー: ${res.error}`);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#039;');
}

function sanitizeHtml(dirtyHtml) {
    if (!dirtyHtml) return '';
    if (typeof DOMPurify !== 'undefined' && DOMPurify.sanitize) {
        return DOMPurify.sanitize(dirtyHtml);
    }
    // フォールバック: スクリプトタグ、iframe、危険な属性・スキームを除去
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(dirtyHtml, 'text/html');
        const dangerousTags = ['script', 'iframe', 'object', 'embed', 'form', 'base', 'meta', 'link'];
        dangerousTags.forEach(tag => {
            doc.querySelectorAll(tag).forEach(el => el.remove());
        });
        const allElements = doc.querySelectorAll('*');
        allElements.forEach(el => {
            for (let i = el.attributes.length - 1; i >= 0; i--) {
                const attr = el.attributes[i];
                const name = attr.name.toLowerCase();
                const val = attr.value.trim().toLowerCase();
                if (name.startsWith('on') || val.startsWith('javascript:') || val.startsWith('data:text/html')) {
                    el.removeAttribute(attr.name);
                }
            }
        });
        return doc.body.innerHTML;
    } catch (e) {
        return escapeHtml(dirtyHtml);
    }
}
