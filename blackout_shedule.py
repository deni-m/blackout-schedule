#!/usr/bin/env python3
"""
DTEK Schedule Viewer - Minimalist Multi-Queue Version
"""

import re
import json
import webbrowser
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright


# Конфігурація
# Відображувані назви населених пунктів / районів для черг
# Додайте/змініть за потреби. Якщо для черги немає назви – буде показано тільки номер.
QUEUE_NAMES = {
    "6.1": "Бобриця",
    "3.1": "Стоянка",  # розкоментуйте і додайте реальну назву
    "3.2": "Софіївська Борщагівка - Радісна, 6",
}
OUTPUT_FILE = "dtek_schedule.html"
DTEK_URL = "https://dtek-krem.com.ua/ua/shutdowns"
HEADLESS = True

# GitHub Pages configuration
GITHUB_PAGES_ENABLED = False  # Set to True to enable GitHub Pages push
GITHUB_PAGES_REPO_PATH = None  # Path to your GitHub Pages repo (e.g., "/path/to/github-pages-repo")


async def fetch_page_with_playwright():
    """Завантажити сторінку через Playwright"""
    print("🎭 Запускаю Playwright...")    
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='uk-UA',
                timezone_id='Europe/Kiev'
            )
            
            page = await context.new_page()
            
            print(f"🌐 Завантаження: {DTEK_URL}")
            await page.goto(DTEK_URL, wait_until='networkidle', timeout=30000)
            
            print("⏳ Чекаю на дані...")
            await page.wait_for_timeout(3000)
            
            html = await page.content()
            
            print("✅ HTML отримано")
            await browser.close()
            
            return html
            
    except Exception as e:
        print(f"❌ Помилка Playwright: {e}")
        return None


def extract_schedule_data(html):
    """Витягти DisconSchedule.fact з HTML"""
    print("🔍 Шукаю дані DisconSchedule.fact...")
    
    try:
        # Виправлений регексп
        pattern = r'DisconSchedule\.fact\s*=\s*(\{.*\})'
        match = re.search(pattern, html, re.DOTALL)
        
        if not match:
            print("❌ Не знайдено DisconSchedule.fact")
            return None
        
        json_str = match.group(1)
        data = json.loads(json_str)
        
        print("✅ Дані розпарсено!")
        return data
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None


def get_schedules_for_queues(data, queues):
    """Отримати графіки для списку черг"""
    
    if 'data' not in data:
        return None
    
    timestamps = list(data['data'].keys())
    if not timestamps:
        return None
    
    result = {}
    
    for queue in queues:
        queue_id = f"GPV{queue}"
        schedules = []
        
        for timestamp in timestamps:
            date = datetime.fromtimestamp(int(timestamp))
            day_data = data['data'][timestamp]
            
            if queue_id in day_data:
                schedules.append({
                    'timestamp': timestamp,
                    'date': date.strftime('%Y-%m-%d'),
                    'date_formatted': date.strftime('%d.%m.%Y'),
                    'schedule': day_data[queue_id]
                })
        
        if schedules:
            result[queue] = schedules
    
    return result


def generate_minimal_html(queues_data, update_time, dtek_update_time=None, queue_names=None):
    """Створити мінімалістичний HTML"""

    if not queues_data:
        return None

    html = f'''<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DTEK Графік</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 10px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 15px;
        }}

        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e0e0e0;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .title {{
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
            flex-grow: 1;
        }}

        .header-info {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            align-items: flex-end;
            font-size: 0.85em;
        }}

        .update-time {{
            color: #666;
            font-size: 0.9em;
        }}

        .dtek-update-time {{
            color: #999;
            font-size: 0.85em;
        }}
        
        .queue-section {{
            margin-bottom: 30px;
        }}
        
        .queue-header {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 10px;
        }}

        .queue-title {{
            font-size: 1.1em;
            font-weight: 600;
            color: #444;
            line-height: 1.3;
        }}

        .date-title {{
            color: #666;
            font-size: 0.9em;
            line-height: 1.4;
        }}
        
        .timeline {{
            display: flex;
            height: 50px;
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid #ddd;
            margin-bottom: 15px;
            gap: 1px;
            background: #f0f0f0;
        }}

        .hour {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7em;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
            min-width: 0;
        }}

        .hour:hover {{
            filter: brightness(1.15);
        }}

        .hour::after {{
            content: attr(data-time);
            font-size: 0.8em;
            opacity: 0.9;
            font-weight: 700;
        }}
        
        .status-yes {{
            background: #4caf50;
        }}
        
        .status-no {{
            background: #f44336;
        }}
        
        .status-first, .status-second {{
            background: #ff9800;
        }}
        
        .status-unknown {{
            background: #9e9e9e;
        }}
        
        .legend {{
            display: flex;
            gap: 15px;
            padding: 12px;
            background: #f9f9f9;
            border-radius: 4px;
            margin-top: 15px;
            font-size: 0.85em;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .legend-color {{
            width: 18px;
            height: 18px;
            border-radius: 3px;
            flex-shrink: 0;
        }}
        
        .separator {{
            height: 1px;
            background: #e0e0e0;
            margin: 20px 0;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 8px;
            }}

            .container {{
                padding: 12px;
                border-radius: 6px;
            }}

            .header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
                padding-bottom: 10px;
                margin-bottom: 12px;
            }}

            .title {{
                font-size: 1.15em;
            }}

            .header-info {{
                align-items: flex-start;
            }}

            .queue-section {{
                margin-bottom: 20px;
            }}

            .queue-title {{
                font-size: 1em;
            }}

            .date-title {{
                font-size: 0.85em;
            }}

            .timeline {{
                height: 45px;
                gap: 0.5px;
            }}

            .hour {{
                font-size: 0.65em;
            }}

            .hour::after {{
                font-size: 0.75em;
            }}

            .separator {{
                margin: 15px 0;
            }}

            .legend {{
                padding: 10px;
                gap: 12px;
                font-size: 0.8em;
            }}

            .legend-color {{
                width: 16px;
                height: 16px;
            }}
        }}

        @media (max-width: 480px) {{
            body {{
                padding: 5px;
            }}

            .container {{
                padding: 10px;
            }}

            .title {{
                font-size: 1.05em;
            }}

            .queue-title {{
                font-size: 0.95em;
            }}

            .timeline {{
                height: 40px;
            }}

            .hour {{
                font-size: 0.6em;
            }}

            .hour::after {{
                font-size: 0.7em;
            }}

            .legend {{
                padding: 8px;
                gap: 10px;
                font-size: 0.75em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">⚡ DTEK Графік відключень</div>
            <div class="header-info">
                <div class="update-time">Згенеровано: {update_time}</div>
                {f'<div class="dtek-update-time">Дата оновлення ДТЕК: {dtek_update_time}</div>' if dtek_update_time else ''}
            </div>
        </div>
'''
    
    # Додати секції для кожної черги
    for queue, schedules in queues_data.items():
        html += f'<div class="queue-section">'
        
        for schedule_data in schedules:
            date = schedule_data['date_formatted']
            schedule = schedule_data['schedule']
            
            # Статистика
            power_on = sum(1 for h in range(1, 25) if schedule.get(str(h)) == 'yes')
            power_off = sum(1 for h in range(1, 25) if schedule.get(str(h)) == 'no')
            
            html += f'''
            <div class="queue-header">
                <div class="queue-title">Черга {queue} - { (queue_names or {}).get(queue, '').strip() }</div>
                <div class="date-title">{date} (✅ {power_on}год / ❌ {power_off}год)</div>
            </div>
            
            <div class="timeline">
'''
            
            # Додати години
            for hour in range(1, 25):
                status = schedule.get(str(hour), 'unknown')
                time_display = '00' if hour == 24 else f'{hour:02d}'
                
                status_text = {
                    'yes': 'Світло є',
                    'no': 'Відключено',
                    'first': 'Перші 30хв',
                    'second': 'Другі 30хв',
                    'unknown': 'Невідомо'
                }.get(status, 'Невідомо')
                
                html += f'''
                <div class="hour status-{status}" 
                     data-time="{time_display}"
                     title="{time_display}:00 - {status_text}">
                </div>
'''
            
            html += '''
            </div>
'''
        
        html += '</div>'
        
        # Розділювач між чергами
        if queue != list(queues_data.keys())[-1]:
            html += '<div class="separator"></div>'
    
    # Легенда
    html += '''
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color status-yes"></div>
                <span>Світло є</span>
            </div>
            <div class="legend-item">
                <div class="legend-color status-no"></div>
                <span>Відключено</span>
            </div>
            <div class="legend-item">
                <div class="legend-color status-first"></div>
                <span>Часткове (30хв)</span>
            </div>
        </div>
    </div>
</body>
</html>'''
    
    return html


def save_and_open_html(html, filename):
    """Зберегти HTML і відкрити в браузері"""
    try:
        output_path = Path(filename).absolute()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Файл збережено: {output_path}")

        webbrowser.open(f'file://{output_path}')
        return True

    except Exception as e:
        print(f"❌ Помилка збереження: {e}")
        return False


def push_to_github_pages(html, filename):
    """Завантажити HTML на GitHub Pages"""
    if not GITHUB_PAGES_ENABLED or not GITHUB_PAGES_REPO_PATH:
        return True

    try:
        repo_path = Path(GITHUB_PAGES_REPO_PATH)
        if not repo_path.exists():
            print(f"❌ Шлях GitHub Pages репо не знайдено: {GITHUB_PAGES_REPO_PATH}")
            return False

        # Копіювати файл до репо
        output_file = repo_path / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Файл скопійовано до GitHub Pages: {output_file}")

        # Git commit і push
        try:
            subprocess.run(['git', 'add', str(output_file)], cwd=str(repo_path), check=True, capture_output=True)
            commit_msg = f"Update DTEK schedule: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            subprocess.run(['git', 'commit', '-m', commit_msg], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(['git', 'push'], cwd=str(repo_path), check=True, capture_output=True)

            print("✅ Файл залито на GitHub Pages")
            return True

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Помилка git операцій: {e}")
            print("   Файл збережено локально, але не залито на GitHub")
            return False

    except Exception as e:
        print(f"❌ Помилка при завантаженні на GitHub Pages: {e}")
        return False


async def main_async():
    """Головна асинхронна функція"""
    print("="*60)
    print("⚡ DTEK Schedule Viewer")
    print("="*60)
    print()
    
    # Завантажити сторінку
    html_content = await fetch_page_with_playwright()
    if not html_content:
        return False
    
    print()
    
    # Витягти дані
    data = extract_schedule_data(html_content)
    if not data:
        return False
    
    print()
    
    # Отримати графіки для черг
    print(f"📊 Обробка черг: {', '.join(QUEUE_NAMES.keys())}")
    queues_data = get_schedules_for_queues(data, QUEUE_NAMES.keys())
    
    if not queues_data:
        print(f"\n❌ Жодну чергу не знайдено")
        
        # Показати доступні черги
        if 'data' in data:
            timestamps = list(data['data'].keys())
            if timestamps:
                all_queues = list(data['data'][timestamps[0]].keys())
                queues_display = [q.replace('GPV', '') for q in all_queues[:20]]
                print("\nДоступні черги:")
                print(", ".join(queues_display))
        
        return False
    
    print(f"✅ Знайдено: {len(queues_data)} черг")
    for queue in queues_data:
        print(f"   • Черга {queue}: {len(queues_data[queue])} днів")
    
    print()
    
    # Створити HTML
    print("🎨 Генерація HTML...")
    kyiv_tz = ZoneInfo('Europe/Kyiv')
    update_time = datetime.now(kyiv_tz).strftime('%d.%m.%Y %H:%M')
    dtek_update_time = data.get('update', None)
    html = generate_minimal_html(queues_data, update_time, dtek_update_time, QUEUE_NAMES)
    
    if not html:
        print("\n❌ Помилка генерації HTML")
        return False
    
    print("✅ HTML згенеровано")
    print()

    # Зберегти і відкрити локально
    if not save_and_open_html(html, OUTPUT_FILE):
        return False

    print()

    # Завантажити на GitHub Pages (якщо увімкнено)
    if GITHUB_PAGES_ENABLED:
        print("📤 Завантаження на GitHub Pages...")
        push_to_github_pages(html, OUTPUT_FILE)

    print()
    print("="*60)
    print("✅ ГОТОВО!")
    print("="*60)
    print()
    return True


def main():
    """Головна функція"""
    
    result = asyncio.run(main_async())
    

if __name__ == "__main__":
    main()