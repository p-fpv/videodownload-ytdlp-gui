let selectedVideo = null;
let selectedAudio = null;
let currentTaskId = null;
let progressInterval = null;
let hasAutoDownloaded = false; 
let currentFilename = null;
const USER_KEY = 'ytdlp_web_user_id';

// Хранилище всех полученных форматов для фильтрации
let rawVideoFormats = [];
let rawAudioFormats = [];

let userId = localStorage.getItem(USER_KEY);
if (!userId) {
    userId = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem(USER_KEY, userId);
}

window.onload = function() {
    checkStatus();
};

async function checkStatus() {
    const formData = new FormData();
    formData.append('user_id', userId);
    try {
        const response = await fetch('/check_status', { method: 'POST', body: formData });
        const data = await response.json();
        
        if (data.status === 'no_task' || data.status === 'cancelled' || data.status === 'cancelled_cleaned') {
            if (document.getElementById('download-actions').style.display === 'block' || 
                document.getElementById('progress-area').style.display === 'block') {
                 resetUI(true); 
            }
            return;
        }

        if (response.ok && data.status) {
            restoreSession(data);
        }
    } catch (e) {
        console.log("Нет старых задач");
    }
}

// Функция применения фильтра
function applyFilter() {
    const isHttpsOnly = document.getElementById('https-only').checked;
    
    // Фильтруем видео
    const filteredVideo = isHttpsOnly 
        ? rawVideoFormats.filter(f => f.protocol.includes('https')) 
        : rawVideoFormats;
        
    // Фильтруем аудио
    const filteredAudio = isHttpsOnly 
        ? rawAudioFormats.filter(f => f.protocol.includes('https')) 
        : rawAudioFormats;

    renderTable('video-table', filteredVideo, 'video');
    renderTable('audio-table', filteredAudio, 'audio');
}

function restoreSession(data) {
    document.getElementById('selection-area').style.display = 'none'; 
    currentTaskId = data.task_id || data; 
    
    if (data.status === 'downloading' || data.status === 'processing') {
        document.getElementById('input-area').style.display = 'none';
        document.getElementById('progress-area').style.display = 'block';
        document.getElementById('progress-init-area').style.display = 'none';
        document.getElementById('stop-download-btn').style.display = 'block';
        document.getElementById('download-actions').style.display = 'none';
        progressInterval = setInterval(() => checkProgress(currentTaskId), 500);
    } else if (data.status === 'finished') {
        document.getElementById('input-area').style.display = 'flex';
        document.getElementById('progress-area').style.display = 'block';
        document.getElementById('progress-init-area').style.display = 'none';
        document.getElementById('stop-download-btn').style.display = 'none';
        showFinishedState(data.filename, data.file_lifetime_min);
    }
}

async function cancelCurrentDownload() {
    if (!currentTaskId) return;
    if (!confirm('Вы уверены, что хотите остановить и отменить загрузку?')) return;
    try {
        const response = await fetch(`/cancel/${currentTaskId}`, { method: 'POST' });
        if (response.ok) {
            clearInterval(progressInterval);
            resetUI(false);
        }
    } catch (e) {
        alert('Ошибка отмены: ' + e.message);
    }
}

function showFinishedState(filename, lifetime) {
    currentFilename = filename;
    const link = document.getElementById('final-download-link');
    // Кодируем имя файла для URL
    link.href = `/get_file/${userId}/${currentTaskId}/${encodeURIComponent(filename)}`;
    link.download = filename;
    document.getElementById('download-actions').style.display = 'block';
    const bar = document.getElementById('progress-bar');
    bar.style.width = '100%';
    bar.innerText = 'Готово!';
    bar.style.backgroundColor = '#28a745';
    
    let statusText = 'Файл готов к скачиванию';
    if (lifetime !== undefined && lifetime !== null) {
        statusText += ` ( время жизни файла ${lifetime} мин, ввод новой ссылки его удалит сразу )`;
    }
    document.getElementById('progress-status').innerText = statusText;
}

function getProtocolHtml(proto) {
    if (!proto) return '';
    let className = 'proto-http';
    if (proto.includes('https')) className = 'proto-https';
    if (proto.includes('m3u8')) className = 'proto-m3u8';
    return `<span class="proto ${className}">${proto}</span>`;
}

async function fetchFormats() {
    const url = document.getElementById('videoUrl').value;
    const errorDiv = document.getElementById('error-msg');
    const loading = document.getElementById('loading');
    const area = document.getElementById('selection-area');
    const btn = document.getElementById('btn-fetch');
    
    if (!url) return;
    
    errorDiv.style.display = 'none';
    loading.style.display = 'block';
    btn.disabled = true;
    
    document.getElementById('progress-area').style.display = 'none';
    document.getElementById('stop-download-btn').style.display = 'none';
    document.getElementById('download-actions').style.display = 'none';

    const formData = new FormData();
    formData.append('url', url);
    formData.append('user_id', userId);
    
    try {
        const response = await fetch('/get_formats', { method: 'POST', body: formData });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка сервера');
        }
        document.getElementById('video-title').innerText = data.title;
        
        // Сохраняем полные списки форматов
        rawVideoFormats = data.video;
        rawAudioFormats = data.audio;
        
        area.style.display = 'block';
        document.getElementById('progress-init-area').style.display = 'block';
        
        // Применяем фильтр (таблицы отрисуются с учетом галочки)
        applyFilter();
        
    } catch (err) {
        errorDiv.innerText = err.message;
        errorDiv.style.display = 'block';
        area.style.display = 'none';
        document.getElementById('progress-init-area').style.display = 'none';
    } finally {
        loading.style.display = 'none';
        btn.disabled = false;
    }
}

function renderTable(tableId, formats, type) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    tbody.innerHTML = '';
    if (formats.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#999;">Нет доступных форматов</td></tr>';
        return;
    }
    formats.forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="format-id">${f.id}</span></td>
            <td>${f.note}</td>
            <td>${getProtocolHtml(f.protocol)}</td>
            <td>${f.size}</td>
        `;
        tr.onclick = () => selectRow(tr, type, f.id);
        tbody.appendChild(tr);
    });
}

function selectRow(row, type, id) {
    const table = row.parentElement;
    Array.from(table.children).forEach(r => r.classList.remove('selected'));
    row.classList.add('selected');
    if (type === 'video') selectedVideo = id;
    if (type === 'audio') selectedAudio = id;
}

async function startDownload() {
    const url = document.getElementById('videoUrl').value;
    hasAutoDownloaded = false;
    currentFilename = null;
    if (!url) return;
    if (!selectedVideo && !selectedAudio) {
        alert('Пожалуйста, выберите хотя бы одну дорожку.');
        return;
    }

    document.getElementById('input-area').style.display = 'none';
    document.getElementById('selection-area').style.display = 'none';
    document.getElementById('progress-init-area').style.display = 'none';
    
    document.getElementById('progress-area').style.display = 'block';
    document.getElementById('stop-download-btn').style.display = 'block';
    document.getElementById('download-actions').style.display = 'none';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-bar').innerText = 'Запуск...';

    const formData = new FormData();
    formData.append('url', url);
    formData.append('user_id', userId);
    if (selectedVideo) formData.append('video_id', selectedVideo);
    if (selectedAudio) formData.append('audio_id', selectedAudio);

    try {
        const response = await fetch('/download_custom', { method: 'POST', body: formData });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка запуска');
        }
        currentTaskId = data.task_id;
        progressInterval = setInterval(() => checkProgress(currentTaskId), 500);
    } catch (err) {
        alert('Ошибка: ' + err.message);
        resetUI(false); 
    }
}

async function checkProgress(id) {
    if (!id) return;
    try {
        const response = await fetch(`/progress/${id}`);
        const data = await response.json();
        
        if (data.status === 'cancelled' || data.status === 'not_found') {
            clearInterval(progressInterval);
            resetUI(false);
            return;
        }

        const bar = document.getElementById('progress-bar');
        const statusTxt = document.getElementById('progress-status');
        const speedTxt = document.getElementById('progress-speed');
        const stopBtn = document.getElementById('stop-download-btn');

        if (data.status === 'downloading') {
            const pct = Math.floor(data.progress || 0);
            bar.style.width = pct + '%';
            bar.innerText = pct + '%';
            statusTxt.innerText = 'Скачивание...';
            speedTxt.innerText = data.speed || '';
            stopBtn.style.display = 'block';
        } else if (data.status === 'processing') {
            bar.style.width = '100%';
            bar.innerText = 'Обработка...';
            statusTxt.innerText = 'Склейка видео и аудио (FFmpeg)';
            speedTxt.innerText = '';
            stopBtn.style.display = 'block';
        } else if (data.status === 'finished') {
            clearInterval(progressInterval);
            stopBtn.style.display = 'none';
            showFinishedState(data.filename, data.file_lifetime_min);
            if (!hasAutoDownloaded) {
                hasAutoDownloaded = true;
                const a = document.createElement('a');
                a.href = document.getElementById('final-download-link').href;
                a.download = currentFilename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
            currentTaskId = null;
            document.getElementById('input-area').style.display = 'flex';
        } else if (data.status === 'error') {
            clearInterval(progressInterval);
            alert('Ошибка скачивания: ' + data.error);
            resetUI(false);
        }
    } catch (err) {
        console.error(err);
    }
}

function resetUI(resetInput = true) {
    if (progressInterval) clearInterval(progressInterval);
    currentTaskId = null;
    hasAutoDownloaded = false;
    currentFilename = null;
    selectedVideo = null;
    selectedAudio = null;

    document.getElementById('progress-area').style.display = 'none';
    document.getElementById('progress-init-area').style.display = 'block';
    document.getElementById('download-actions').style.display = 'none';
    document.getElementById('stop-download-btn').style.display = 'none';
    
    document.getElementById('selection-area').style.display = 'none';
    
    document.getElementById('input-area').style.display = 'flex';

    if (resetInput) {
        document.getElementById('videoUrl').value = '';
    }
    
    const bar = document.getElementById('progress-bar');
    bar.style.width = '0%';
    bar.style.backgroundColor = '#007BFF';
    bar.innerText = '';
}