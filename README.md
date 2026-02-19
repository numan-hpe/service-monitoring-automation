# Service Monitoring Automation

Automates Grafana and Humio dashboard monitoring and report generation.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Settings
Edit `config.py`:
- Set your `USER_EMAIL`
- Update dashboard URLs if needed

### 3. Run Automation

**Run everything (Grafana + Humio):**
```bash
python service_monitoring_automation.py
```

**Run only Grafana:**
```bash
python service_monitoring_automation.py --graphana
```

**Run only Humio:**
```bash
python service_monitoring_automation.py --humio
```

## What It Does

1. Opens a browser window
2. Logs into dashboards (you'll need to authenticate with fingerprint/password)
3. Collects monitoring data
4. Generates reports in `reports/YYYY-MM-DD/` folder
5. Keeps browser open for review

## Reports Generated

- **Grafana**: PDF report with metrics and screenshots
- **Humio**: Text report with error summaries

## Time Range

Default: Last 24 hours from now

To change, edit `config.py`:
```python
# Grafana time range
GRAPHANA_FROM = "now-24h"  # Last 24 hours
GRAPHANA_TO = "now"

# Humio time range
HUMIO_FROM = "now-1d"     # Last 1 day
HUMIO_TO = "now"
```

**Common time range options (works for both Grafana and Humio):**
- `now-1h` = Last 1 hour
- `now-24h` or `now-1d` = Last 24 hours (today)
- `now-7d` = Last 7 days (last week)
- `now-30d` = Last 30 days (last month)

**Examples:**

Get last week's Grafana data only:
```python
GRAPHANA_FROM = "now-7d"
GRAPHANA_TO = "now"
```
```

Get last 3 days of Humio errors only:
```python
HUMIO_FROM = "now-3d"
HUMIO_TO = "now"
```
```

Get both Grafana (last 24h) and Humio (last 2 days):
```python
GRAPHANA_FROM = "now-24h"
GRAPHANA_TO = "now"
HUMIO_FROM = "now-2d"
HUMIO_TO = "now"
```
