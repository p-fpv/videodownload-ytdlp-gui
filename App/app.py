# ==========================================
# НАСТРОЙКИ АВТОРИЗАЦИИ
# ==========================================
USE_AUTH = False          # True = Нужен пароль, False = Доступ без логина
ADMIN_USER = "qwer"
ADMIN_PASS = "543210"
# ==========================================

# ==========================================
# НАСТРОЙКИ ПРОКСИ
# ==========================================
USE_PROXY = False
# USE_PROXY = True
PROXY_URL = "socks5://127.0.0.1:10808/"
# ==========================================


import os
import yt_dlp
import threading
import uuid
import re
import time
import logging
import shutil
from functools import wraps
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory, session, redirect, url_for
import webbrowser

# ==========================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ==========================================
server_logger = logging.getLogger('ytdlp_server')
server_logger.setLevel(logging.INFO)

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
server_logger.addHandler(file_handler)
# ==========================================

app = Flask(__name__, template_folder='site')
app.secret_key = 'change_this_secret_key_to_something_securergsfdsrgfvdc' 

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
FFMPEG_PATH = os.path.join(BASE_DIR, 'ffmpeg.exe')

tasks = {}
threads = {}
user_tasks = {}

MAX_FILE_AGE = 3600
CLEANUP_INTERVAL = 60

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем включена ли защита
        if USE_AUTH:
            if not session.get('logged_in'):
                server_logger.warning(f"ACCESS_DENIED | IP: {request.remote_addr} | Path: {request.path}")
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

if not os.path.isfile(FFMPEG_PATH):
    print("-" * 50)
    print(f"КРИТИЧЕСКАЯ ОШИБКА: Файл {FFMPEG_PATH} НЕ НАЙДЕН!")
    print("-" * 50)

def get_user_dir(user_id):
    u_dir = os.path.join(DOWNLOAD_FOLDER, user_id)
    if not os.path.exists(u_dir):
        os.makedirs(u_dir)
    return u_dir

def get_session_dir(user_id, task_id):
    s_dir = os.path.join(DOWNLOAD_FOLDER, user_id, task_id)
    if not os.path.exists(s_dir):
        os.makedirs(s_dir)
    return s_dir

def get_size_value(f, duration=None):
    exact = f.get('filesize')
    approx = f.get('filesize_approx')
    if exact:
        return exact / (1024*1024)
    if approx:
        return approx / (1024*1024)
    if duration:
        tbr = f.get('tbr')
        if tbr:
            estimated_bytes = (duration * tbr * 1000) / 8
            return estimated_bytes / (1024*1024)
    return 0.0

def get_formatted_size(f, duration=None):
    exact = f.get('filesize')
    approx = f.get('filesize_approx')
    if exact:
        return f"{exact / (1024*1024):.1f} MB"
    if approx:
        return f"~{approx / (1024*1024):.1f} MB"
    if duration:
        tbr = f.get('tbr')
        if tbr:
            estimated_bytes = (duration * tbr * 1000) / 8
            return f"~{estimated_bytes / (1024*1024):.1f} MB"
    return "-"

def get_ydl_opts(download=False, user_id=None, task_id=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH,
        'socket_timeout': 5,  # Ваше изменение
        'fragment_retries': 20, # Ваше изменение
        'retries': 20,          # Ваше изменение
    }
    if USE_PROXY and PROXY_URL:
        opts['proxy'] = PROXY_URL
    if download and user_id and task_id:
        session_dir = get_session_dir(user_id, task_id)
        opts.update({
            'outtmpl': os.path.join(session_dir, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
        })
    return opts

def clean_ansi(text):
    if not text: return ""
    text = re.sub(r'(\x1b\[[0-9;]*m|\[[0-9;]+m)', '', text)
    return text.strip()

def cleanup_thread():
    print(">> Автоочистка запущена")
    while True:
        try:
            now = time.time()
            if os.path.exists(DOWNLOAD_FOLDER):
                for user_id in os.listdir(DOWNLOAD_FOLDER):
                    user_dir = os.path.join(DOWNLOAD_FOLDER, user_id)
                    if os.path.isdir(user_dir):
                        for sess_id in os.listdir(user_dir):
                            sess_dir = os.path.join(user_dir, sess_id)
                            if os.path.isdir(sess_dir):
                                for f in os.listdir(sess_dir):
                                    path = os.path.join(sess_dir, f)
                                    if os.path.isfile(path):
                                        if now - os.path.getmtime(path) > MAX_FILE_AGE:
                                            try:
                                                os.remove(path)
                                            except: pass
                                if not os.listdir(sess_dir):
                                    try:
                                        os.rmdir(sess_dir)
                                    except: pass
                        if not os.listdir(user_dir):
                            try:
                                os.rmdir(user_dir)
                            except: pass
        except Exception: pass
        time.sleep(CLEANUP_INTERVAL)

cleaner = threading.Thread(target=cleanup_thread, daemon=True)
cleaner.start()

def download_thread(task_id, url, format_selector, user_id):
    session_dir = get_session_dir(user_id, task_id)
    
    def progress_hook(d):
        if tasks.get(task_id, {}).get('status') == 'cancelled':
            return 
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%')
            clean_percent_text = clean_ansi(percent_str)
            match = re.search(r'(\d+\.?\d*)', clean_percent_text)
            if match:
                tasks[task_id]['progress'] = float(match.group(1))
            else:
                tasks[task_id]['progress'] = 0.0
            speed_str = d.get('_speed_str', 'N/A')
            tasks[task_id]['speed'] = clean_ansi(speed_str)
            tasks[task_id]['status'] = 'downloading'
        elif d['status'] == 'finished':
            tasks[task_id]['status'] = 'processing'

    try:
        opts = get_ydl_opts(download=True, user_id=user_id, task_id=task_id)
        opts['format'] = format_selector
        opts['progress_hooks'] = [progress_hook]
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for f in os.listdir(session_dir):
                    if f.startswith(base):
                        filename = os.path.join(session_dir, f)
                        break
            if tasks[task_id]['status'] == 'cancelled':
                try:
                    shutil.rmtree(session_dir)
                    print(f"[DOWNLOAD] Отмененная сессия удалена: {user_id}/{task_id}")
                except: pass
                return
            tasks[task_id]['status'] = 'finished'
            tasks[task_id]['filename'] = os.path.basename(filename)
    except Exception as e:
        if tasks[task_id]['status'] != 'cancelled':
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = str(e)
    finally:
        if task_id in threads:
            del threads[task_id]

def bg_cleanup_worker(user_id, old_task_id):
    print(f"[BG-CLEANUP] Запущен для {user_id}, сессия {old_task_id}...")
    thread = threads.get(old_task_id)
    if thread:
        print(f"[BG-CLEANUP] Ожидание завершения потока {old_task_id}...")
        thread.join(timeout=10.0)
    
    session_dir = get_session_dir(user_id, old_task_id)
    
    if os.path.exists(session_dir):
        retries = 10
        for i in range(retries):
            try:
                shutil.rmtree(session_dir)
                print(f"[BG-CLEANUP] Сессия {old_task_id} успешно удалена.")
                user_dir = get_user_dir(user_id)
                try:
                    os.rmdir(user_dir)
                    print(f"[BG-CLEANUP] Папка пользователя {user_id} удалена (была пуста).")
                except OSError:
                    pass
                return
            except PermissionError as e:
                print(f"[BG-CLEANUP] Попытка {i+1}: {e}. Ждем 2 сек...")
                time.sleep(2)
            except Exception as e:
                print(f"[BG-CLEANUP] Ошибка удаления: {e}")
                break
        print(f"[BG-CLEANUP] Не удалось удалить сессию {old_task_id} после всех попыток. Оставляем.")
    else:
        print(f"[BG-CLEANUP] Папка сессии {old_task_id} уже отсутствует.")

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если авторизация отключена, сразу перекидываем на главную
    if not USE_AUTH:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            server_logger.info(f"LOGIN_SUCCESS | User: {username} | IP: {request.remote_addr}")
            return redirect(url_for('index'))
        else:
            server_logger.warning(f"LOGIN_FAIL | User: {username} | IP: {request.remote_addr}")
            return render_template('login.html', error=True)
    return render_template('login.html', error=False)

@app.route('/logout')
def logout():
    server_logger.info(f"LOGOUT | IP: {request.remote_addr}")
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    # Если авторизация включена, проверяем сессию
    if USE_AUTH:
        if not session.get('logged_in'):
            return redirect(url_for('login'))
    return render_template('index.html')

# ИСПРАВЛЕНИЕ: Убран декоратор @login_required, чтобы стили и скрипты грузились на странице входа
@app.route('/site/<path:filename>')
def serve_static(filename):
    return send_from_directory('site', filename)

@app.route('/cancel/<task_id>', methods=['POST'])
@login_required
def cancel_task(task_id):
    task = tasks.get(task_id)
    if task:
        task['status'] = 'cancelled'
        if user_tasks.get(task.get('user_id')) == task_id:
            del user_tasks[task['user_id']]
        server_logger.info(f"CANCEL_DOWNLOAD | IP: {request.remote_addr} | TaskID: {task_id}")
        return jsonify({'status': 'cancelled'})
    return jsonify({'status': 'not_found'}), 404

@app.route('/check_status', methods=['POST'])
@login_required
def check_status():
    user_id = request.form.get('user_id')
    if not user_id: return jsonify({'status': 'no_user'}), 400
    task_id = user_tasks.get(user_id)
    if not task_id: return jsonify({'status': 'no_task'})
    task = tasks.get(task_id)
    if not task: return jsonify({'status': 'no_task'})
    
    if 'task_id' not in task: task['task_id'] = task_id
    if 'user_id' not in task: task['user_id'] = user_id
    
    if task['status'] == 'finished':
        task['file_lifetime_min'] = MAX_FILE_AGE // 60
        try:
            file_path = os.path.join(get_session_dir(user_id, task_id), task['filename'])
            if not os.path.exists(file_path):
                print(f"[CHECK_STATUS] Файл не найден, сброс задачи {task_id}")
                del user_tasks[user_id]
                if task_id in tasks: del tasks[task_id]
                try:
                    session_dir = get_session_dir(user_id, task_id)
                    if os.path.exists(session_dir): os.rmdir(session_dir)
                except: pass
                return jsonify({'status': 'no_task'})
        except Exception as e:
            print(f"[CHECK_STATUS] Ошибка проверки: {e}")
            return jsonify({'status': 'no_task'})
    return jsonify(task)

@app.route('/get_formats', methods=['POST'])
@login_required
def get_formats():
    url = request.form.get('url')
    user_id = request.form.get('user_id')
    if not url: return jsonify({'error': 'URL не предоставлен'}), 400
    if not user_id: return jsonify({'error': 'Нет ID пользователя'}), 400
    
    server_logger.info(f"GET_FORMATS | IP: {request.remote_addr} | URL: {url[:50]}...")
    
    if user_id in user_tasks:
        old_task_id = user_tasks[user_id]
        if old_task_id in tasks:
            tasks[old_task_id]['status'] = 'cancelled'
        del user_tasks[user_id]

        cleaner_thread = threading.Thread(target=bg_cleanup_worker, args=(user_id, old_task_id))
        cleaner_thread.start()

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(download=False)) as ydl:
            info = ydl.extract_info(url, download=False)
        
        duration = info.get('duration')
        formats = info.get('formats', [])
        video_formats = []
        audio_formats = []
        for f in formats:
            protocol = f.get('protocol', 'unknown')
            size_str = get_formatted_size(f, duration)
            size_val = get_size_value(f, duration) 
            
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            if vcodec != 'none':
                ext = f.get('ext').upper()
                res = f.get('resolution') or f.get('format_note') or "unknown"
                fps = f.get('fps') or ""
                note_text = f"{res} {ext} {fps}fps".strip()
                if acodec != 'none': note_text += " [+Аудио]"
                video_formats.append({'id': f['format_id'], 'ext': ext, 'note': note_text, 'size': size_str, 'size_val': size_val, 'protocol': protocol})
            elif vcodec == 'none':
                ext = f.get('ext').upper()
                abr = f.get('abr')
                note = f"{ext}, {abr} kbps" if abr else ext
                audio_formats.append({'id': f['format_id'], 'ext': ext, 'note': note, 'size': size_str, 'size_val': size_val, 'protocol': protocol})
        
        video_formats.sort(key=lambda x: x['size_val'], reverse=True)
        audio_formats.sort(key=lambda x: x['size_val'], reverse=True)
        
        return jsonify({'title': info.get('title'), 'video': video_formats, 'audio': audio_formats})
    except Exception as e:
        server_logger.error(f"ERROR_GET_FORMATS | IP: {request.remote_addr} | Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_custom', methods=['POST'])
@login_required
def download_custom():
    url = request.form.get('url')
    video_id = request.form.get('video_id')
    audio_id = request.form.get('audio_id')
    user_id = request.form.get('user_id')
    if not url: return jsonify({'error': 'URL отсутствует'}), 400
    if not user_id: return jsonify({'error': 'Нет ID пользователя'}), 400
    if video_id and audio_id:
        format_selector = f"{video_id}+{audio_id}"
    elif video_id:
        format_selector = video_id
    elif audio_id:
        format_selector = audio_id
    else:
        return jsonify({'error': 'Формат не выбран'}), 400
    task_id = str(uuid.uuid4())
    get_session_dir(user_id, task_id)
    tasks[task_id] = {
        'status': 'started', 'progress': 0, 'speed': 'N/A', 'filename': None, 'task_id': task_id, 'user_id': user_id
    }
    user_tasks[user_id] = task_id
    
    server_logger.info(f"START_DOWNLOAD | IP: {request.remote_addr} | V_ID: {video_id} | A_ID: {audio_id} | TaskID: {task_id}")
    
    thread = threading.Thread(target=download_thread, args=(task_id, url, format_selector, user_id))
    threads[task_id] = thread
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
@login_required
def progress(task_id):
    task = tasks.get(task_id)
    if not task: return jsonify({'status': 'not_found'}), 404
    if task.get('status') == 'finished' and 'file_lifetime_min' not in task:
        task['file_lifetime_min'] = MAX_FILE_AGE // 60
    return jsonify(task)

@app.route('/get_file/<user_id>/<task_id>/<filename>')
@login_required
def get_file(user_id, task_id, filename):
    file_path = os.path.join(get_session_dir(user_id, task_id), filename)
    if os.path.exists(file_path):
        server_logger.info(f"FILE_DOWNLOAD | IP: {request.remote_addr} | File: {filename}")
        
        # RFC 5987 кодирование для UTF-8 имён
        import urllib.parse
        encoded_name = urllib.parse.quote(filename)
        
        response = send_file(file_path, as_attachment=True)
        response.headers['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_name}'
        return response
    return "File not found", 404

if __name__ == '__main__':
    if os.path.exists(DOWNLOAD_FOLDER):
        try:
            print(">> Очистка папки downloads перед запуском...")
            shutil.rmtree(DOWNLOAD_FOLDER)
            print(">> Папка downloads очищена.")
        except Exception as e:
            print(f">> ВНИМАНИЕ: Не удалось очистить папку downloads при запуске: {e}")
    
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    print("\n" + "="*40)
    print("  Сервер запущен!")
    if USE_AUTH:
        print(f"  Режим: Защищенный (Требуется пароль)")
        print(f"  Login: {ADMIN_USER}")
        print(f"  Password: {ADMIN_PASS}")
    else:
        print(f"  Режим: Открытый (Пароль не требуется)")

    if USE_PROXY:
        print(f"  Используется прокси: {PROXY_URL} настройки USE_PROXY/PROXY_URL в ./App/app.py")
    else:
        print(f"  Встроенный прокси yt-dlp выключен, настройки USE_PROXY/PROXY_URL в ./App/app.py")
        
    print(f"  Откройте в браузере: http://127.0.0.1:8000")
    print(f"  Логирование включено: server.log")
    print("="*40 + "\n")
    webbrowser.open('http://127.0.0.1:8000')
    app.run(host='0.0.0.0', port=8000, debug=False)