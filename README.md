# VIDEO DOWNLOAD

Веб-приложение для скачивания видео с YouTube и других платформ через `yt-dlp`.

## Возможности

- Скачивание видео и аудио в различных форматах
- Выбор качества и формата
- Встроенный FFmpeg для конвертации
- Простой веб-интерфейс
- Портативная установка (не требует системного Python)

## Требования

- Windows (x64)
- Интернет-соединение (для загрузки Python и FFmpeg при установке)

## Установка

### Вариант 1: Скачать ZIP-архив

1. Нажмите **Code** → **Download ZIP** на GitHub
2. Распакуйте архив в любую папку
3. Запустите `other\install_or_update_requirements.bat`

### Вариант 2: Через Git

```bash
git clone https://github.com/p-fpv/videodownload-ytdlp-gui.git
cd videodownload-ytdlp-gui
other\install_or_update_requirements.bat
```

## Запуск

Запустите `START.bat` — откроется браузер с адресом `http://127.0.0.1:8000`

## Обновление

Запустите `update_main.bat` — скрипт:
- Проверит наличие Git (при необходимости скачает портативный)
- Скачает последние файлы из репозитория
- Обновит Python-зависимости

## Удаление зависимостей

Запустите `other\uninstall_requirements.bat` — удалит:
- Портативный Python
- FFmpeg
- Временные файлы и загрузки

После этого можно запустить `other\install_or_update_requirements.bat` для чистой установки.

## Настройки

### Авторизация

Откройте `App\app.py` и измените:

```python
USE_AUTH = True          # Включить защиту паролем
ADMIN_USER = "admin"     # Логин
ADMIN_PASS = "password"  # Пароль
```

### Прокси

Для работы через прокси измените в `App\app.py`:

```python
USE_PROXY = True
PROXY_URL = "socks5://127.0.0.1:10808/"
```

## Структура проекта

```
videodownload-ytdlp-gui/
├── App/
│   ├── app.py                 # Основной сервер
│   ├── requirements.txt       # Python зависимости
│   └── site/                  # Веб-интерфейс
│       ├── index.html
│       ├── login.html
│       ├── script.js
│       └── style.css
├── other/                     # Скрипты установки/удаления
│   ├── install_or_update_requirements.bat
│   └── uninstall_requirements.bat
├── START.bat                  # Запуск приложения
└── update_main.bat            # Обновление из репозитория
```

## Технологии

- **Backend:** Python + Flask
- **Загрузка:** yt-dlp
- **Конвертация:** FFmpeg
- **Frontend:** HTML, CSS, JavaScript

## Лицензия

GPL v3
