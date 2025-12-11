#!/usr/bin/env python3
"""
DTEK Schedule Viewer - Minimalist Multi-Queue Version
"""

import re
import json
import webbrowser
import asyncio
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


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
HEADLESS = True  # Set to False for local testing if Incapsula blocks headless mode

# GitHub Pages configuration
GITHUB_PAGES_ENABLED = False  # Set to True to enable GitHub Pages push
GITHUB_PAGES_REPO_PATH = None  # Path to your GitHub Pages repo (e.g., "/path/to/github-pages-repo")


async def fetch_page_with_playwright():
    """Завантажити сторінку через Playwright"""
    print("🎭 Запускаю Playwright...")

    try:
        async with async_playwright() as p:
            # Launch with better stealth arguments to bypass Incapsula
            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-setuid-sandbox'
                ]
            )

            # Better context with more realistic settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='uk-UA',
                timezone_id='Europe/Kiev',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )

            # Hide webdriver property
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Hide chrome property
                window.navigator.chrome = {
                    runtime: {}
                };

                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            page = await context.new_page()

            print(f"🌐 Завантаження: {DTEK_URL}")
            await page.goto(DTEK_URL, wait_until='load', timeout=60000)

            print("⏳ Чекаю на дані (обхід Incapsula)...")
            # Wait for Incapsula challenge to complete and actual content to load
            # Look for specific content that should be on the DTEK page
            try:
                # Try to wait for the main content div or any specific DTEK element
                await page.wait_for_selector('body', timeout=5000)
                print("   ✅ Сторінка завантажена")

                # Give more time for Incapsula challenge
                await page.wait_for_timeout(20000)

                # Check if we're still on Incapsula page
                page_content = await page.content()
                if 'Incapsula' in page_content and len(page_content) < 2000:
                    print("   ⚠️  Incapsula challenge виявлено, чекаю довше...")
                    await page.wait_for_timeout(30000)

            except Exception as e:
                print(f"   ⚠️  Помилка очікування: {e}")

            # Try to wait for network idle
            try:
                await page.wait_for_load_state('networkidle', timeout=20000)
                print("   ✅ Networkidle досягнуто")
            except Exception as e:
                print(f"   ⚠️  Timeout на networkidle: {e}")

            # Additional wait for JavaScript to execute
            await page.wait_for_timeout(5000)

            html = await page.content()

            # Додаємо інформацію про розмір сторінки для відлагодження
            print(f"   Отримано HTML розміром: {len(html)} байт")
            
            print("✅ HTML отримано")
            await browser.close()
            
            return html
            
    except Exception as e:
        print(f"❌ Помилка Playwright: {e}")
        import traceback
        print("📋 Stack trace:")
        traceback.print_exc()
        return None


def extract_schedule_data(html):
    """Витягти DisconSchedule.fact з HTML"""
    print("🔍 Шукаю дані DisconSchedule.fact...")

    try:
        if not html:
            print("❌ HTML порожній або не завантажено")
            return None

        print(f"   HTML розмір: {len(html)} символів")

        # Виправлений регексп
        pattern = r'DisconSchedule\.fact\s*=\s*(\{.*\})'
        match = re.search(pattern, html, re.DOTALL)

        if not match:
            print("❌ Не знайдено DisconSchedule.fact у HTML")
            print("   Перевіряю, чи сторінка завантажилась правильно...")
            if 'shutdowns' in html:
                print("   ℹ️  Сторінка завантажилась, але дані не знайдені (можливо, JS не виконав)")
            else:
                print("   ℹ️  Сторінка не містить очікуваного контенту")
            return None

        json_str = match.group(1)
        print(f"   Знайдено JSON рядок довжиною {len(json_str)} символів")

        try:
            data = json.loads(json_str)
            print(f"✅ Дані розпарсено! Знайдено записів: {len(data.get('data', {}))}")
            return data
        except json.JSONDecodeError as je:
            print(f"❌ Помилка парсингу JSON: {je}")
            print(f"   Перші 200 символів JSON: {json_str[:200]}")
            return None

    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        print("📋 Stack trace:")
        traceback.print_exc()
        return None


def get_schedules_for_queues(data, queues):
    """Отримати графіки для списку черг"""

    if 'data' not in data:
        return None

    timestamps = list(data['data'].keys())
    if not timestamps:
        return None

    result = {}
    kyiv_tz = ZoneInfo('Europe/Kyiv')

    for queue in queues:
        queue_id = f"GPV{queue}"
        schedules = []

        for timestamp in timestamps:
            date = datetime.fromtimestamp(int(timestamp), tz=kyiv_tz)
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
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>⚡</text></svg>">
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
            overflow: visible;
            border: 1px solid #ddd;
            margin-bottom: 30px;
            margin-top: 25px;
            gap: 1px;
            background: #f0f0f0;
            position: relative;
        }}

        .hour {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 4px 2px;
            gap: 3px;
            font-size: 0.7em;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
            min-width: 0;
            line-height: 1.5;
        }}

        .hour:hover {{
            filter: brightness(1.15);
        }}

        .hour-start {{
            font-size: 1.2em;
            font-weight: 500;
            opacity: 0.9;
        }}

        .hour-end {{
            font-size: 1.2em;
            font-weight: 500;
            opacity: 0.9;
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

        /* Current time indicator styles */
        .hour.current-hour {{
            box-shadow: 0 0 0 2px #1a1a1a, inset 0 0 0 200px rgba(255, 255, 255, 0.5);
            position: relative;
            z-index: 10;
        }}

        .hour.current-hour::after {{
            content: '▲';
            position: absolute;
            bottom: -20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 16px;
            color: #1a1a1a;
            filter: drop-shadow(0 2px 3px rgba(255,255,255,0.8));
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }}
            50% {{
                opacity: 0.6;
                transform: translateX(-50%) translateY(-3px);
            }}
        }}

        .outage-block-label {{
            position: absolute;
            top: -22px;
            background: transparent;
            color: #f44336;
            border: 2px solid #f44336;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.75em;
            font-weight: 700;
            z-index: 5;
            white-space: nowrap;
            pointer-events: none;
        }}

        .power-on-label {{
            position: absolute;
            top: -22px;
            background: transparent;
            color: #4caf50;
            border: 2px solid #4caf50;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.75em;
            font-weight: 700;
            z-index: 5;
            white-space: nowrap;
            pointer-events: none;
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
                padding: 3px 1px;
            }}

            .hour-start, .hour-end {{
                font-size: 0.9em;
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
                padding: 2px 1px;
            }}

            .hour-start, .hour-end {{
                font-size: 0.8em;
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
    kyiv_tz = ZoneInfo('Europe/Kyiv')
    today = datetime.now(kyiv_tz).date()

    for queue, schedules in queues_data.items():
        html += f'<div class="queue-section">'

        for schedule_data in schedules:
            date = schedule_data['date_formatted']
            date_obj = datetime.strptime(schedule_data['date'], '%Y-%m-%d').date()
            schedule = schedule_data['schedule']

            # Статистика
            power_on_full = sum(1 for h in range(1, 25) if schedule.get(str(h)) == 'yes')
            power_off_full = sum(1 for h in range(1, 25) if schedule.get(str(h)) == 'no')
            partial = sum(1 for h in range(1, 25) if schedule.get(str(h)) in ['first', 'second'])

            # Рахуємо загальний час:
            # - При 'first'/'second': 30хв БЕЗ світла + 30хв ЗІ світлом
            total_power_on = power_on_full + (partial * 0.5)
            total_power_off = power_off_full + (partial * 0.5)

            # Перевірка чи графік попередній (всі години "yes" для майбутньої дати)
            is_future = date_obj > today
            is_preliminary = is_future and power_on_full == 24 and power_off_full == 0 and partial == 0

            preliminary_label = ' ⚠️ <span style="color: #ff9800; font-weight: normal;">Попередній графік</span>' if is_preliminary else ''

            # Формуємо рядок статистики
            # Показуємо десяткове значення тільки якщо є залишок (наприклад, 12.5), інакше ціле число
            if total_power_on % 1 == 0 and total_power_off % 1 == 0:
                stats_text = f'✅ {int(total_power_on)}год / ❌ {int(total_power_off)}год'
            elif total_power_on % 1 == 0:
                stats_text = f'✅ {int(total_power_on)}год / ❌ {total_power_off:.1f}год'
            elif total_power_off % 1 == 0:
                stats_text = f'✅ {total_power_on:.1f}год / ❌ {int(total_power_off)}год'
            else:
                stats_text = f'✅ {total_power_on:.1f}год / ❌ {total_power_off:.1f}год'

            html += f'''
            <div class="queue-header">
                <div class="queue-title">Черга {queue} - { (queue_names or {}).get(queue, '').strip() }</div>
                <div class="date-title">{date} ({stats_text}){preliminary_label}</div>
            </div>

            <div class="timeline">
'''
            
            # Додати години (починаємо з опівночі - 0:00)
            for hour in range(1, 25):
                status = schedule.get(str(hour), 'unknown')
                # Відображаємо години від 0 до 23
                hour_display_start = hour - 1
                hour_display_end = hour if hour < 24 else 0

                status_text = {
                    'yes': 'Світло є',
                    'no': 'Відключено',
                    'first': 'Перші 30хв',
                    'second': 'Другі 30хв',
                    'unknown': 'Невідомо'
                }.get(status, 'Невідомо')

                html += f'''
                <div class="hour status-{status}"
                     data-hour="{hour_display_start}"
                     data-date="{schedule_data['date']}"
                     title="{hour_display_start:02d}:00 - {hour_display_end:02d}:00 ({status_text})">
                    <span class="hour-start">{hour_display_start}</span>
                    <span class="hour-end">{hour_display_end}</span>
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
    <script>
        // Function to add block labels
        function addBlockLabels() {
            // Get all timelines
            const timelines = document.querySelectorAll('.timeline');
            console.log('Found timelines:', timelines.length);

            timelines.forEach((timeline, timelineIndex) => {
                // Remove existing labels
                timeline.querySelectorAll('.outage-block-label, .power-on-label').forEach(label => label.remove());

                // Get all hour cells in this timeline
                const hours = Array.from(timeline.querySelectorAll('.hour'));

                // Function to find blocks based on classifier
                function findBlocks(classifier) {
                    let blocks = [];
                    let currentBlock = null;

                    hours.forEach((hour, index) => {
                        const matches = classifier(hour);

                        if (matches) {
                            if (!currentBlock) {
                                currentBlock = { start: index, end: index, cells: [hour] };
                            } else {
                                currentBlock.end = index;
                                currentBlock.cells.push(hour);
                            }
                        } else {
                            if (currentBlock) {
                                blocks.push(currentBlock);
                                currentBlock = null;
                            }
                        }
                    });

                    if (currentBlock) {
                        blocks.push(currentBlock);
                    }

                    return blocks;
                }

                // Find outage blocks (red + orange)
                const outageBlocks = findBlocks(hour =>
                    hour.classList.contains('status-no') ||
                    hour.classList.contains('status-first') ||
                    hour.classList.contains('status-second')
                );

                // Find power-on blocks (green)
                const powerOnBlocks = findBlocks(hour => hour.classList.contains('status-yes'));

                console.log(`Timeline ${timelineIndex}: Found ${outageBlocks.length} outage blocks, ${powerOnBlocks.length} power-on blocks`);

                // Function to create label for a block
                function createLabel(block, isOutage) {
                    // Calculate duration
                    let duration = 0;
                    block.cells.forEach(cell => {
                        if (cell.classList.contains('status-no') || cell.classList.contains('status-yes')) {
                            duration += 1;
                        } else if (cell.classList.contains('status-first') || cell.classList.contains('status-second')) {
                            duration += 0.5;
                        }
                    });

                    const firstCell = block.cells[0];
                    const lastCell = block.cells[block.cells.length - 1];

                    // Calculate position
                    const firstRect = firstCell.getBoundingClientRect();
                    const lastRect = lastCell.getBoundingClientRect();
                    const timelineRect = timeline.getBoundingClientRect();

                    const left = firstRect.left - timelineRect.left;
                    const width = lastRect.right - firstRect.left;

                    // Create label
                    const label = document.createElement('div');
                    label.className = isOutage ? 'outage-block-label' : 'power-on-label';
                    label.textContent = duration % 1 === 0 ? duration : duration.toFixed(1);
                    label.style.left = `${left}px`;
                    label.style.width = `${width}px`;
                    label.style.textAlign = 'center';

                    timeline.appendChild(label);
                }

                // Create labels for outage blocks
                outageBlocks.forEach(block => createLabel(block, true));

                // Create labels for power-on blocks
                powerOnBlocks.forEach(block => createLabel(block, false));
            });
        }

        // Function to highlight the current hour
        function highlightCurrentHour() {
            // Get current time in user's local timezone
            const now = new Date();
            const currentHour = now.getHours();
            const currentDate = now.toISOString().split('T')[0]; // Format: YYYY-MM-DD

            // Remove previous highlights
            document.querySelectorAll('.hour.current-hour').forEach(el => {
                el.classList.remove('current-hour');
            });

            // Find and highlight ALL current hour cells (for all queues on the same day)
            const currentCells = document.querySelectorAll(`.hour[data-hour="${currentHour}"][data-date="${currentDate}"]`);
            if (currentCells.length > 0) {
                currentCells.forEach(cell => {
                    cell.classList.add('current-hour');
                });
                // Scroll to the first one
                currentCells[0].scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
            }
        }

        // Run on page load
        window.addEventListener('load', () => {
            // Use requestAnimationFrame to ensure layout is complete
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    addBlockLabels();
                    highlightCurrentHour();
                });
            });
        });

        // Update every minute
        setInterval(highlightCurrentHour, 60000);

        // Re-calculate labels on window resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(addBlockLabels, 100);
        });
    </script>
</body>
</html>'''

    return html


def generate_all_groups_html(data, update_time, dtek_update_time=None):
    """Створити HTML з усіма групами у простому форматі"""

    if not data or 'data' not in data:
        return None

    kyiv_tz = ZoneInfo('Europe/Kyiv')
    today = datetime.now(kyiv_tz).date()
    tomorrow = today + timedelta(days=1)

    # Отримати всі доступні черги
    timestamps = list(data['data'].keys())
    if not timestamps:
        return None

    # Створити словник: timestamp_str -> (date_obj, schedules_dict)
    dates_data = []
    for timestamp in timestamps:
        date_obj = datetime.fromtimestamp(int(timestamp), tz=kyiv_tz).date()
        dates_data.append((date_obj, data['data'][timestamp]))

    # Сортувати за датою
    dates_data.sort(key=lambda x: x[0])

    # HTML початок
    html = f'''<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DTEK - Всі групи</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>⚡</text></svg>">
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
            max-width: 1400px;
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
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e0e0e0;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .title {{
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
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

        .date-section {{
            margin-bottom: 30px;
        }}

        .date-section-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 4px;
        }}

        .hours-row {{
            margin-bottom: 4px;
            background: transparent;
        }}

        .hours-row:hover {{
            background: transparent;
        }}

        .hours-row .hour {{
            background: transparent;
            border: none;
            color: #666;
            font-size: 0.75em;
            padding: 2px;
            gap: 2px;
        }}

        .hour-label-start {{
            font-weight: 600;
        }}

        .hour-label-end {{
            font-weight: 400;
            font-size: 0.9em;
        }}

        .group-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            padding: 5px;
            border-radius: 4px;
        }}

        .group-row:hover {{
            background: #f9f9f9;
        }}

        .group-number {{
            min-width: 60px;
            font-weight: 600;
            color: #444;
            font-size: 0.95em;
        }}

        .timeline {{
            display: flex;
            flex: 1;
            height: 35px;
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid #ddd;
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
            min-width: 0;
        }}

        .status-yes {{
            background: #4caf50;
        }}

        .status-no {{
            background: #f44336;
        }}

        .status-first {{
            background: #ff9800;
        }}

        .status-second {{
            background: #ff9800;
        }}

        .status-unknown {{
            background: #9e9e9e;
        }}

        @media (max-width: 768px) {{
            .group-number {{
                min-width: 50px;
                font-size: 0.85em;
            }}

            .timeline {{
                height: 30px;
            }}

            .hours-row .hour {{
                font-size: 0.65em;
            }}
        }}

        @media (max-width: 480px) {{
            .group-row {{
                flex-direction: column;
                align-items: flex-start;
                gap: 5px;
            }}

            .hours-row {{
                display: none;
            }}

            .timeline {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">⚡ DTEK - Всі групи</div>
            <div class="header-info">
                <div class="update-time">Згенеровано: {update_time}</div>
                {f'<div class="update-time">Дата оновлення ДТЕК: {dtek_update_time}</div>' if dtek_update_time else ''}
            </div>
        </div>
'''

    # Додати секції для кожної дати
    for target_date, date_label in [(today, 'Сьогодні'), (tomorrow, 'Завтра')]:
        # Знайти дані для цієї дати
        schedules = None
        for date_obj, date_schedules in dates_data:
            if date_obj == target_date:
                schedules = date_schedules
                break

        if not schedules:
            continue

        date_formatted = target_date.strftime('%d.%m.%Y')

        html += f'''
        <div class="date-section">
            <div class="date-section-title">{date_label} ({date_formatted})</div>
            <div class="group-row hours-row">
                <div class="group-number"></div>
                <div class="timeline">
'''

        # Додати мітки годин як перший рядок
        for hour in range(1, 25):
            hour_start = hour - 1
            hour_end = hour if hour < 24 else 0
            html += f'''
                    <div class="hour hour-label">
                        <span class="hour-label-start">{hour_start}</span>
                        <span class="hour-label-end">{hour_end}</span>
                    </div>
'''

        html += '''
                </div>
            </div>
'''

        # Отримати всі групи та відсортувати
        queue_ids = sorted(schedules.keys())

        for queue_id in queue_ids:
            schedule = schedules[queue_id]
            # Видалити префікс GPV для відображення
            display_id = queue_id.replace('GPV', '')

            html += f'''
            <div class="group-row">
                <div class="group-number">{display_id}</div>
                <div class="timeline">
'''

            # Додати години
            for hour in range(1, 25):
                status = schedule.get(str(hour), 'unknown')
                hour_start = hour - 1
                hour_end = hour if hour < 24 else 0

                status_text = {
                    'yes': 'Світло є',
                    'no': 'Відключено',
                    'first': 'Перші 30хв',
                    'second': 'Другі 30хв',
                    'unknown': 'Невідомо'
                }.get(status, 'Невідомо')

                html += f'''
                    <div class="hour status-{status}"
                         title="{hour_start:02d}:00-{hour_end:02d}:00 ({status_text})"></div>
'''

            html += '''
                </div>
            </div>
'''

        html += '''
        </div>
'''

    html += '''
    </div>
</body>
</html>'''

    return html


def save_and_open_html(html, filename):
    """Зберегти HTML і відкрити в браузері"""
    try:
        if not html:
            print(f"❌ HTML порожній, не можна зберегти")
            return False

        output_path = Path(filename).absolute()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Файл збережено: {output_path}")
        print(f"   Розмір файлу: {len(html)} символів")

        try:
            webbrowser.open(f'file://{output_path}')
        except Exception as web_err:
            print(f"⚠️  Не вдалось відкрити браузер (GitHub Actions не підтримує): {web_err}")

        return True

    except Exception as e:
        print(f"❌ Помилка збереження: {e}")
        import traceback
        print("📋 Stack trace:")
        traceback.print_exc()
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
    print("1️⃣  Завантаження сторінки з DTEK...")
    html_content = await fetch_page_with_playwright()
    if not html_content:
        print("\n⚠️  КРИТИЧНА ПОМИЛКА: Не вдалось завантажити сторінку")
        print("   Можливі причини:")
        print("   - Проблема з мережею")
        print("   - Сервер DTEK недоступний")
        print("   - Playwright не встановлено або пошкоджено")
        return False

    print()

    # Зберегти raw HTML для відлагодження (BEFORE parsing, so we can debug)
    try:
        html_debug_path = Path("dtek_raw_page.html").absolute()
        with open(html_debug_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Raw HTML збережено для відлагодження: {html_debug_path}")
    except Exception as e:
        print(f"⚠️  Не вдалось зберегти raw HTML: {e}")

    # Витягти дані
    print("2️⃣  Парсинг HTML...")
    data = extract_schedule_data(html_content)
    if not data:
        print("\n⚠️  КРИТИЧНА ПОМИЛКА: Не вдалось розпарсити дані")
        print("   Можливі причини:")
        print("   - Структура сторінки DTEK змінилась")
        print("   - JavaScript не виконав (потребує більше часу)")
        print("   - Сторінка повернула помилку")
        print(f"   📄 Перевірте raw HTML: {html_debug_path}")
        return False

    # Зберегти JSON дані
    try:
        json_path = Path("dtek_schedule_data.json").absolute()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON дані збережено: {json_path}")
    except Exception as e:
        print(f"⚠️  Не вдалось зберегти JSON: {e}")

    print()
    
    # Отримати графіки для черг
    print(f"3️⃣  Фільтрування черг...")
    print(f"   Шукаю черги: {', '.join(QUEUE_NAMES.keys())}")
    queues_data = get_schedules_for_queues(data, QUEUE_NAMES.keys())

    if not queues_data:
        print(f"\n⚠️  ПОМИЛКА: Жодну чергу не знайдено")
        print(f"   Розгорнуто шукати черги: {', '.join(QUEUE_NAMES.keys())}")

        # Показати доступні черги
        if 'data' in data:
            timestamps = list(data['data'].keys())
            if timestamps:
                all_queues = list(data['data'][timestamps[0]].keys())
                queues_display = [q.replace('GPV', '') for q in all_queues[:20]]
                print(f"\n   📋 Доступні черги на сервері ({len(all_queues)} всього):")
                print(f"   {', '.join(queues_display)}")
                if len(all_queues) > 20:
                    print(f"   ... і ще {len(all_queues) - 20}")
        else:
            print("   ℹ️  Структура даних неочікувана, немає 'data' ключа")

        return False
    
    print(f"✅ Знайдено: {len(queues_data)} черг")
    for queue in queues_data:
        print(f"   • Черга {queue}: {len(queues_data[queue])} днів")
    
    print()

    # Створити HTML
    print("4️⃣  Генерація HTML...")
    try:
        kyiv_tz = ZoneInfo('Europe/Kyiv')
        update_time = datetime.now(kyiv_tz).strftime('%d.%m.%Y %H:%M')
        dtek_update_time = data.get('update', None)
        print(f"   Час оновлення: {update_time}")
        html = generate_minimal_html(queues_data, update_time, dtek_update_time, QUEUE_NAMES)

        if not html:
            print("\n❌ Помилка генерації HTML (функція повернула None)")
            return False

        print(f"✅ HTML згенеровано ({len(html)} символів)")
    except Exception as e:
        print(f"\n❌ Помилка при генерації HTML: {e}")
        import traceback
        print("📋 Stack trace:")
        traceback.print_exc()
        return False

    print()

    # Зберегти і відкрити локально
    print("5️⃣  Збереження файлу...")
    if not save_and_open_html(html, OUTPUT_FILE):
        print("\n❌ Помилка при збереженні файлу")
        return False

    print()

    # Створити та зберегти сторінку з усіма групами
    print("6️⃣  Генерація сторінки з усіма групами...")
    try:
        html_all = generate_all_groups_html(data, update_time, dtek_update_time)

        if html_all:
            all_groups_file = "dtek_schedule_all.html"
            if save_and_open_html(html_all, all_groups_file):
                print(f"✅ Сторінка з усіма групами збережена")
            else:
                print(f"⚠️  Не вдалось зберегти сторінку з усіма групами")
        else:
            print("⚠️  Не вдалось згенерувати HTML з усіма групами")
    except Exception as e:
        print(f"⚠️  Помилка при генерації сторінки з усіма групами: {e}")
        import traceback
        traceback.print_exc()

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