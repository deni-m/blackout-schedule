# Project Context and Technical Documentation

This document contains architectural decisions, technical context, and important implementation details for the DTEK Blackout Schedule Viewer project.

## Project Overview

**Purpose**: Automated scraping and visualization of DTEK power outage schedules
**Primary Language**: Python 3
**Key Technology**: Playwright (headless browser automation)
**Output Format**: Standalone HTML files with embedded CSS/JS

## Architecture

### High-Level Flow

```
DTEK Website
    ↓ (Playwright scraping)
Raw HTML
    ↓ (Regex parsing)
JSON Data (DisconSchedule.fact)
    ↓ (Python processing)
HTML Generation
    ↓
Static HTML Files (with inline CSS/JS)
```

### Component Breakdown

#### 1. Web Scraping Layer (`fetch_page_with_playwright`)
- **Technology**: Playwright with Chromium
- **Challenge**: Website requires JavaScript execution and has loading delays
- **Approach**: Browser automation with realistic settings (user agent, viewport, wait times)
- **Timing**: 20-30 second wait for page to fully load

#### 2. Data Extraction Layer (`extract_schedule_data`)
- **Method**: Regex search for `DisconSchedule.fact = {...}` in raw HTML
- **Format**: JSON object embedded in JavaScript
- **Structure**:
  ```json
  {
    "data": {
      "1702252800": {  // Unix timestamp
        "GPV6.1": {     // Queue ID
          "1": "yes",   // Hour 1 (00:00-01:00)
          "2": "no",    // Hour 2 (01:00-02:00)
          ...
        }
      }
    },
    "update": "timestamp or date string"
  }
  ```

#### 3. Schedule Processing (`get_schedules_for_queues`)
- Filters data for configured queues
- Converts Unix timestamps to dates (Kyiv timezone)
- Structures data for HTML generation

#### 4. HTML Generation (`generate_minimal_html`, `generate_all_groups_html`)
- Creates self-contained HTML with inline CSS and JavaScript
- Responsive design using flexbox
- Embedded SVG favicon

## Important Technical Decisions

### 1. Time Handling

**Server-Side Time (Python)**:
- **Purpose**: Determine which schedules to display (today/tomorrow)
- **Timezone**: Europe/Kyiv (hardcoded)
- **Usage**: Used at page generation time only
- **Location**: Lines 594, 847, 1310

**Client-Side Time (JavaScript)**:
- **Purpose**: Highlight current hour in the timeline
- **Source**: User's browser local time (`new Date()`)
- **Updates**: Every 60 seconds via `setInterval`
- **Location**: Lines 791-811

**Rationale**: Server time determines content; client time provides real-time UI updates without page refresh.

### 2. Hour Display Convention

**Internal Representation**: Hours 1-24 (API format from DTEK)
**Display Format**: Hours 0-23 (standard time format)

Example:
- Hour `"1"` from API → displays as `0-1` (00:00-01:00)
- Hour `"24"` from API → displays as `23-0` (23:00-00:00)

**Location**: Lines 640-662

### 3. Status Types

| Value | Meaning | Display Color |
|-------|---------|---------------|
| `"yes"` | Power ON (full hour) | Green (#4caf50) |
| `"no"` | Power OFF (full hour) | Red (#f44336) |
| `"first"` | OFF first 30min, ON second 30min | Orange (#ff9800) |
| `"second"` | ON first 30min, OFF second 30min | Orange (#ff9800) |
| `"unknown"` | No data | Gray (#9e9e9e) |

### 4. Statistics Calculation

Partial hours (`first`/`second`) count as 0.5 hours for each status:
- `first`/`second`: 0.5h power OFF + 0.5h power ON
- Total power ON = (full hours with "yes") + (partial hours × 0.5)
- Total power OFF = (full hours with "no") + (partial hours × 0.5)

**Location**: Lines 605-629

### 5. Preliminary Schedule Detection

A schedule is marked as "preliminary" if:
- Date is in the future (after today)
- All 24 hours show `"yes"`
- No partial or "no" hours

**Rationale**: DTEK often publishes placeholder "all green" schedules for future dates.

**Location**: Lines 614-618

### 6. Favicon Implementation

**Format**: SVG embedded as data URI
**Icon**: Lightning bolt emoji (⚡)
**Rationale**: No external dependencies, works offline, thematically appropriate

**Location**: Lines 242, 872

### 7. Current Hour Highlighting

**Implementation**:
- Uses CSS class `current-hour`
- Matches both hour AND date (handles multi-queue displays)
- Selector: `.hour[data-hour="${currentHour}"][data-date="${currentDate}"]`
- Auto-scrolls to first match on page load

**Visual Indicators**:
- Black border with white overlay (box-shadow + rgba)
- Animated triangle marker below the cell
- Pulsing animation

**Location**: Lines 388-415, 791-811

### 8. Block Duration Labels

**Feature**: Shows duration of consecutive power-on/off blocks
**Implementation**:
- JavaScript calculates blocks on page load and window resize
- Positioned absolutely above timeline using `getBoundingClientRect()`
- Red border labels for outages, green for power-on periods

**Location**: Lines 693-788

## Data Flow Details

### Input: DTEK Website Structure

The DTEK website loads schedule data via JavaScript:
```javascript
DisconSchedule.fact = {
  "data": { ... },
  "update": "..."
}
```

This is embedded in the page HTML and executed client-side.

### Output: Standalone HTML

Generated HTML files are completely self-contained:
- No external CSS files
- No external JavaScript files
- No external images (SVG favicon is inline)
- Works offline after generation
- Can be hosted on any static server

## Performance Considerations

### Scraping Performance
- **Total time**: ~30-50 seconds per run
- **Bottleneck**: Page loading and JavaScript execution (20-30s wait)
- **Browser overhead**: Chromium launch (~2-5s)

### HTML Generation Performance
- **Time**: < 1 second
- **File size**:
  - Personalized view: ~45KB
  - All groups view: ~90KB

### Browser Rendering Performance
- **JavaScript execution**: Runs once on load + on resize
- **Animation**: CSS-only (GPU accelerated)
- **Update interval**: 60 seconds (minimal CPU usage)

## Known Issues and Limitations

### 1. Page Loading Issues
**Issue**: Sometimes page takes longer to load or fails
**Workaround**: Increase wait times, run in non-headless mode for debugging
**Location**: Lines 111-118

### 2. Timezone Hardcoded
**Issue**: Kyiv timezone is hardcoded
**Impact**: Users outside Ukraine see incorrect "today/tomorrow"
**Rationale**: DTEK operates only in Ukraine, schedules are Kyiv-time based

### 3. Client Time for Highlighting
**Issue**: Current hour highlight uses client local time
**Impact**: If user is in different timezone, wrong hour is highlighted
**Rationale**: Most users are in Ukraine; shows "current hour for you"

### 4. Static HTML Requires Regeneration
**Issue**: Schedules don't update automatically
**Solution**: Run script periodically (cron/scheduled task)

## Future Enhancement Ideas

### Potential Improvements

1. **Timezone Auto-detection**: Convert schedules to user's local timezone
2. **Progressive Web App**: Add service worker for offline functionality
3. **Browser Extension**: Chrome/Firefox extension with background updates
4. **Notification System**: Browser notifications before outages
5. **Historical Data**: Track schedule accuracy over time
6. **API Server**: Serve JSON data via REST API
7. **Docker Container**: Containerized deployment
8. **Mobile App**: React Native or Flutter mobile app

### Code Improvements

1. **Error Recovery**: Better handling of partial failures
2. **Rate Limiting**: Avoid hammering DTEK servers
3. **Caching**: Cache responses to reduce scraping frequency
4. **Testing**: Unit tests for parsing and HTML generation
5. **Configuration File**: Move config to external YAML/JSON
6. **Logging**: Structured logging with log levels

## Development Guidelines

### Adding New Queues

Edit `QUEUE_NAMES` dictionary:
```python
QUEUE_NAMES = {
    "6.1": "Your Location Name",
}
```

Queue format: `"{group}.{subgroup}"` (e.g., "6.1", "3.2")

### Debugging Failed Scrapes

1. Check `dtek_raw_page.html` - raw HTML from website
2. Check `dtek_schedule_data.json` - parsed JSON data
3. Run with `HEADLESS = False` to see browser
4. Check for Incapsula/Cloudflare blocks

### Modifying Styles

All CSS is inline in the HTML generation functions:
- Main schedule: `generate_minimal_html()` (line 236+)
- All groups: `generate_all_groups_html()` (line 865+)

Colors defined at lines 372-386, 1006-1024

### Testing HTML Changes

Generate sample data and test locally:
```python
# Use existing JSON file instead of scraping
with open('dtek_schedule_data.json') as f:
    data = json.load(f)
```

## Security Considerations

1. **No User Data**: Script doesn't collect or store user information
2. **No Authentication**: No credentials or API keys required
3. **No External Requests**: Generated HTML makes no external calls
4. **Static Output**: HTML files are static, no server-side code

## Dependencies

### Python Packages
- `playwright` - Browser automation
- `zoneinfo` - Timezone handling (stdlib in Python 3.9+)
- `datetime`, `pathlib`, `json`, `re` - Standard library

### Browser
- Chromium (installed via `playwright install`)

## Git Strategy

### Commit Pattern
Automated commits from GitHub Actions:
- Format: `"Update DTEK schedule - YYYY-MM-DD HH:MM UTC"`
- Frequency: Hourly (via scheduled workflow)

### Ignored Files
Consider adding to `.gitignore`:
```
dtek_raw_page.html
dtek_schedule_data.json
dtek_schedule.html
dtek_schedule_all.html
```

These are generated files and change frequently.

## Maintenance Notes

### Regular Checks
- **Monthly**: Verify DTEK website structure hasn't changed
- **Weekly**: Check script success rate
- **Daily**: Monitor GitHub Actions success rate

### Breaking Changes to Watch For
1. DTEK website redesign
2. Different JavaScript variable name (not `DisconSchedule.fact`)
3. Changed JSON structure
4. Changes to page loading behavior

## Contact and Support

For issues specific to this implementation, check:
1. `dtek_raw_page.html` - raw data
2. Console output - error messages
3. GitHub Issues - known problems

---

**Last Updated**: 2025-12-11
**Python Version**: 3.8+
**Playwright Version**: Latest (1.40+)
