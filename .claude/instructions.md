# Claude Instructions for DTEK Blackout Schedule Viewer

## Project Overview

This is a Python web scraper that fetches DTEK (Ukrainian electricity provider) power outage schedules and generates beautiful, self-contained HTML visualizations. The project prioritizes simplicity, reliability, and offline-capable output.

**Core Philosophy**: Keep it simple. Generate static, self-contained HTML files with no external dependencies.

## Quick Reference

### Project Structure
- `blackout_shedule.py` - Main script (single file, ~1400 lines)
- `dtek_schedule.html` - Generated personalized schedule
- `dtek_schedule_all.html` - Generated all-groups schedule
- `dtek_raw_page.html` - Debug: raw HTML from DTEK
- `dtek_schedule_data.json` - Debug: parsed JSON data

### Key Configuration (top of script)
```python
QUEUE_NAMES = {...}  # User's queues with location names
OUTPUT_FILE = "dtek_schedule.html"
DTEK_URL = "https://dtek-krem.com.ua/ua/shutdowns"
HEADLESS = True
```

## Important Architectural Decisions

### 1. Self-Contained HTML
**Decision**: All CSS and JavaScript are inline in the HTML
**Rationale**: Files work offline, can be hosted anywhere, no build process
**Do**: Keep all styles and scripts embedded
**Don't**: Add external CSS/JS files or CDN links

### 2. Time Handling Split
**Server-side (Python)**: Determines which schedules to show (today/tomorrow)
- Uses `datetime.now(kyiv_tz)` - Kyiv timezone hardcoded
- Lines: 594, 847, 1310

**Client-side (JavaScript)**: Highlights current hour
- Uses `new Date()` - user's local time
- Updates every 60 seconds
- Lines: 791-811

**Do**: Respect this separation - don't mix concerns
**Don't**: Try to sync these or make them use the same source

### 3. Hour Display Convention
**API Format**: Hours 1-24 (from DTEK)
**Display Format**: Hours 0-23 (standard time)
- Hour "1" → displays as "0-1" (00:00-01:00)
- Hour "24" → displays as "23-0" (23:00-00:00)

### 4. Single-File Architecture
**Decision**: Everything in one Python file
**Rationale**: Easy to deploy, no package management, simple automation
**Do**: Keep code in `blackout_shedule.py`
**Don't**: Break into multiple Python modules

## Code Style & Conventions

### Python Style
- Function names: `snake_case`
- Clear docstrings for main functions
- Use f-strings for formatting
- Preserve existing comment style (Ukrainian + English)

### HTML Generation
- Use triple-quoted f-strings for HTML
- Double braces `{{` for CSS (escaping in f-strings)
- Maintain responsive design patterns
- Keep mobile-first approach

### CSS Classes
- `.status-yes` - Green (power on)
- `.status-no` - Red (power off)
- `.status-first` / `.status-second` - Orange (partial)
- `.current-hour` - Current time highlight

## Common Tasks

### Adding a New Visual Feature
1. Locate the relevant HTML generation function:
   - `generate_minimal_html()` - personalized view (line 230)
   - `generate_all_groups_html()` - all groups view (line 840)
2. Add CSS in the inline `<style>` block
3. Add JavaScript in the inline `<script>` block
4. Test by running: `python blackout_shedule.py`

### Modifying the Timeline Display
- Timeline structure: lines 325-350 (CSS), 637-664 (HTML generation)
- Hour cells: lines 337-370 (styling)
- Current hour indicator: lines 388-415 (CSS), 791-811 (JS)
- Block duration labels: lines 416-444 (CSS), 693-788 (JS)

### Changing Colors
- Status colors defined: lines 372-386 (main), 1006-1024 (all groups)
- Update both `generate_minimal_html` and `generate_all_groups_html`

### Debugging Failed Scrapes
1. Check `dtek_raw_page.html` - did we get HTML?
2. Check `dtek_schedule_data.json` - did parsing work?
3. Run with `HEADLESS = False` - watch browser behavior
4. Increase wait time at line 112

## UI Enhancement Features

### Current Hour Indicator
**What it does**: Highlights current hour cell with dark border and arrow pointing up from below

**Key implementation details**:
- Uses `querySelectorAll()` to find ALL matching cells (not just first one)
- Highlights current hour across all queue rows for today
- Updates every 60 seconds
- Uses local browser time (not server/Kyiv time)

**Visual styling**:
- 2px dark border (`#1a1a1a`) with white overlay for visibility on all backgrounds
- Arrow (▲) positioned below cell with white drop-shadow
- `z-index: 10` to appear above other elements

**IMPORTANT**: Always use `querySelectorAll()` when you need to highlight multiple elements. Using `querySelector()` will only find the first match and cause incomplete highlighting.

### Block Duration Labels
**What it does**: Shows duration (in hours) above continuous blocks of same-colored cells

**Types of blocks**:
- **Outage blocks** (red border): Red cells + orange cells (partial outages)
- **Power-on blocks** (green border): Green cells

**Calculation logic**:
- Full hour cells (red/green): count as 1 hour
- Partial hour cells (orange): count as 0.5 hours
- Display whole numbers without decimals, decimals with one place (e.g., "3" or "2.5")

**Positioning**:
- Uses `getBoundingClientRect()` to calculate exact position above each block
- Labels centered over their block span
- Transparent background with colored outline
- Called on page load and window resize

**IMPORTANT**:
- Labels only apply to `dtek_schedule.html` (personalized view)
- NOT applied to `dtek_schedule_all.html` (all groups view)
- Timeline needs `overflow: visible` and extra margin-top/bottom for label space

### Data Attributes for JavaScript Targeting
Hour cells include `data-hour` and `data-date` attributes:
```html
<div class="hour status-yes" data-hour="13" data-date="2025-12-11">
```
- `data-hour`: 0-23 (display format, not API format)
- `data-date`: YYYY-MM-DD format
- Used by JavaScript to find and highlight current hour

## Things to AVOID

### ❌ Don't Add External Dependencies
- No external CSS frameworks (Bootstrap, Tailwind, etc.)
- No JavaScript libraries (jQuery, React, etc.)
- Keep favicon as inline SVG data URI

### ❌ Don't Break Offline Capability
- No API calls from generated HTML
- No external image/font URLs
- No CDN references

### ❌ Don't Mention Security Bypasses
- Don't document "bypassing Incapsula" or similar
- Use neutral terms: "browser automation", "page loading"
- Focus on technical approach, not security measures

### ❌ Don't Hardcode Sensitive Data
- No API keys or credentials (currently none needed)
- No personal queue data in examples

### ⚠️ Be Careful With
- **Wait times**: Lines 111-131 - changing these affects reliability
- **Regex pattern**: Line 163 - critical for data extraction
- **Timezone**: Hardcoded to Kyiv - don't change without good reason
- **Hour mapping**: Lines 640-662 - off-by-one errors are easy

## Testing Guidelines

### Manual Testing
```bash
# Basic test
python blackout_shedule.py

# Check output files exist
ls -la dtek_schedule*.html

# Open in browser
# Verify: current hour highlighted, colors correct, responsive design works
```

### What to Test After Changes

**CSS Changes**:
- [ ] Desktop view (1920x1080)
- [ ] Tablet view (768px)
- [ ] Mobile view (480px)
- [ ] Current hour highlight visible on all queue rows
- [ ] Current hour border (2px dark) visible on all backgrounds (white/red/green/orange)
- [ ] Current hour arrow (▲) visible below cell
- [ ] Duration labels positioned correctly above blocks
- [ ] Duration labels show for both outage (red) and power-on (green) blocks
- [ ] Partial hours (0.5) calculated and displayed correctly

**JavaScript Changes**:
- [ ] Current hour highlights on ALL queue rows (not just first)
- [ ] Current hour highlights on page load
- [ ] Auto-scroll to current hour works
- [ ] Updates every minute
- [ ] Block duration labels appear above continuous blocks
- [ ] Labels recalculate on window resize
- [ ] Console has no errors

**Data Processing Changes**:
- [ ] All configured queues appear
- [ ] Statistics calculate correctly
- [ ] Dates display correctly
- [ ] Preliminary schedules marked

### Quick Debug Checklist
1. Does `dtek_raw_page.html` exist and have content?
2. Does `dtek_schedule_data.json` exist and have valid JSON?
3. Do generated HTML files open without errors?
4. Is console output showing any errors or warnings?

## Helpful Context

### Why Playwright?
- JavaScript execution needed (schedule data loads via JS)
- Handles page loading delays
- More reliable than requests/beautifulsoup for dynamic content

### Why Inline Everything?
- GitHub Pages hosting (simple static files)
- Works offline after generation
- No build process needed
- Easy to share (single file)

### Why Two HTML Files?
- `dtek_schedule.html`: User's queues only (personalized, smaller)
- `dtek_schedule_all.html`: All queues (reference, larger)
- Different use cases, different audiences

### Why 20-30 Second Wait?
- Website takes time to load JavaScript
- Conservative timeout prevents false failures
- Better to wait longer than fail the scrape

## Common Gotchas

### Unicode/Encoding Issues
- Windows console needs UTF-8 setup (lines 17-23)
- Always use `encoding='utf-8'` for file operations
- Test with Ukrainian characters (черга, світло, etc.)

### F-String Braces
- CSS in f-strings needs double braces: `{{` → `{`
- Common error: forgetting to escape braces
- Shows as `KeyError` or `IndexError`

### Hour Off-By-One
- API uses 1-24, display uses 0-23
- Always convert: `hour_display = hour - 1`
- Remember: hour 1 spans 00:00-01:00

### Timezone Confusion
- Python: always Kyiv time
- JavaScript: always local time
- Don't try to make them match!

### querySelector vs querySelectorAll
- `querySelector()` returns only the FIRST matching element
- `querySelectorAll()` returns ALL matching elements
- When highlighting current hour across multiple rows, must use `querySelectorAll()`
- Common mistake: using `querySelector()` results in only first row being highlighted
- Always use `querySelectorAll()` + `forEach()` for multi-element operations

## When Modifying This Project

### Before Making Changes
1. Read relevant section in `PROJECT_CONTEXT.md`
2. Check if change affects both HTML generation functions
3. Consider mobile responsiveness
4. Think about offline capability

### Making Changes
1. Update code
2. Run script: `python blackout_shedule.py`
3. Test generated HTML in browser
4. Check mobile view (DevTools)
5. Verify no console errors

### After Making Changes
1. Update `PROJECT_CONTEXT.md` if architectural decision changed
2. Update `README.md` if user-facing behavior changed
3. Test edge cases (no data, single queue, many queues)
4. Check that debug files still generate correctly

## Useful Line References

| Feature | Lines | Function |
|---------|-------|----------|
| Web scraping | 43-148 | `fetch_page_with_playwright()` |
| Data extraction | 151-192 | `extract_schedule_data()` |
| Queue filtering | 195-227 | `get_schedules_for_queues()` |
| Main HTML gen | 230-837 | `generate_minimal_html()` |
| All groups HTML | 840-1154 | `generate_all_groups_html()` |
| Current hour highlight | 791-811 | JavaScript in HTML |
| Duration labels | 693-788 | JavaScript in HTML |
| Main execution | 1224-1367 | `main_async()` |

## Project Context

- **Created for**: Ukrainian citizens during power outages
- **Primary users**: Ukrainian residents needing schedule visibility
- **Update frequency**: Designed for hourly automated runs
- **Hosting**: GitHub Pages (static site)
- **Language**: Python (script) + Ukrainian (UI text)

## Questions to Ask User Before Big Changes

- "Should the generated HTML remain self-contained?"
- "Do we need to maintain offline capability?"
- "Should this work with automated GitHub Actions?"
- "Are there specific queue numbers this must support?"
- "What's the target update frequency?"

---

**Remember**: This project prioritizes simplicity and reliability over feature richness. When in doubt, choose the simpler solution.
