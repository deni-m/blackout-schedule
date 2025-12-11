# ⚡ DTEK Blackout Schedule Viewer

A Python-based web scraper and visualizer for DTEK (Ukrainian electricity provider) power outage schedules. Generates beautiful, interactive HTML pages showing planned blackout schedules for specific queues/groups.

## Features

- **Automated Web Scraping**: Uses Playwright browser automation to fetch schedule data from DTEK website
- **Interactive Timeline**: Visual 24-hour timeline with color-coded power status
- **Real-time Current Hour Highlighting**: Automatically highlights the current hour based on client's local time
- **Multiple Views**:
  - **Personalized View**: Shows schedules for your configured queues with location names
  - **All Groups View**: Complete schedule for all available queues/groups
- **Smart Statistics**: Shows power on/off hours with support for partial outages (30-minute intervals)
- **Responsive Design**: Mobile-friendly interface that works on all devices
- **Auto-scroll**: Automatically scrolls to the current hour on page load
- **Duration Labels**: Visual labels showing the duration of power-on and power-off blocks

## Requirements

- Python 3.8+
- Playwright browser automation library
- Internet connection

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd blackout-schedule
   ```

2. **Install dependencies**:
   ```bash
   pip install playwright
   ```

3. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

## Configuration

Edit the `blackout_shedule.py` file to configure your queues:

```python
# Configure your queues and location names
QUEUE_NAMES = {
    "6.1": "Бобриця",
    "3.1": "Стоянка",
    "3.2": "Софіївська Борщагівка - Радісна, 6",
}
```

### Other Configuration Options

```python
# Output file name
OUTPUT_FILE = "dtek_schedule.html"

# DTEK source URL
DTEK_URL = "https://dtek-krem.com.ua/ua/shutdowns"

# Browser mode (set to False for debugging)
HEADLESS = True

# GitHub Pages integration (optional)
GITHUB_PAGES_ENABLED = False
GITHUB_PAGES_REPO_PATH = None
```

## Usage

### Basic Usage

Run the script:
```bash
python blackout_shedule.py
```

The script will:
1. Fetch the latest schedule from DTEK website
2. Generate two HTML files:
   - `dtek_schedule.html` - Your personalized view with configured queues
   - `dtek_schedule_all.html` - All available groups
3. Open the HTML files in your default browser
4. Save debug files (`dtek_raw_page.html`, `dtek_schedule_data.json`)

### Automated Updates

To automatically update the schedule, you can set up a cron job or Windows Task Scheduler:

**Linux/Mac (crontab)**:
```bash
# Update every hour
0 * * * * cd /path/to/blackout-schedule && python blackout_shedule.py
```

**Windows Task Scheduler**:
- Create a new task
- Set trigger: repeat every 1 hour
- Action: Run `python.exe` with argument `blackout_shedule.py`

## Understanding the Schedule

### Color Coding

- 🟢 **Green** - Power is ON (full hour)
- 🔴 **Red** - Power is OFF (full hour)
- 🟠 **Orange** - Partial outage (30 minutes off, 30 minutes on)
- ⚫ **Gray** - Unknown status

### Current Time Indicator

The current hour is highlighted with:
- A thick black border
- A white overlay
- A pulsing triangle indicator below

This updates automatically every minute based on your local time.

### Statistics

Each schedule shows:
- ✅ Total hours with power
- ❌ Total hours without power
- Partial hours are counted as 0.5 hours for each status

### Preliminary Schedules

Future dates may show "⚠️ Попередній графік" (Preliminary Schedule) - these are subject to change.

## Output Files

- `dtek_schedule.html` - Main personalized schedule view
- `dtek_schedule_all.html` - Complete view of all groups
- `dtek_raw_page.html` - Raw HTML from DTEK (for debugging)
- `dtek_schedule_data.json` - Parsed JSON data (for debugging)

## Troubleshooting

### Website Loading Issues

If the script fails to fetch data:
1. Set `HEADLESS = False` in the script to debug
2. Run again and observe the browser behavior
3. Increase wait times in the `fetch_page_with_playwright()` function

### No Data Found

Check the following:
1. Verify the queue numbers in `QUEUE_NAMES` are correct
2. Check `dtek_schedule_data.json` to see all available queues
3. Ensure DTEK website is accessible

### Playwright Installation Issues

```bash
# Reinstall Playwright
pip uninstall playwright
pip install playwright
playwright install chromium
```

## GitHub Pages Integration (Optional)

To automatically publish schedules to GitHub Pages:

1. Create a GitHub Pages repository
2. Configure in the script:
   ```python
   GITHUB_PAGES_ENABLED = True
   GITHUB_PAGES_REPO_PATH = "/path/to/your/github-pages-repo"
   ```
3. The script will automatically commit and push updates

## How It Works

1. **Fetches** the DTEK website using Playwright browser automation
2. **Extracts** schedule data from the `DisconSchedule.fact` JavaScript object
3. **Parses** the JSON data structure with queue schedules
4. **Generates** responsive HTML with embedded CSS and JavaScript
5. **Highlights** current time using client-side JavaScript

## License

This project is for personal use. DTEK schedule data belongs to DTEK company.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Credits

Created to help Ukrainian citizens track power outage schedules during difficult times. Stay safe! 🇺🇦
