# Service Monitoring Automation

Automates Grafana and Humio dashboard monitoring and report generation.

## Quick Start

1. Install:
	```bash
	pip install -r requirements.txt
	playwright install chromium
	```
2. Configure:
	- Set `USER_EMAIL` in `config.py`
3. Run:
	```bash
	python service_monitoring_automation.py
	```
	Optional:
	- Grafana only: `python service_monitoring_automation.py --graphana`
	- Humio only: `python service_monitoring_automation.py --humio`

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

**Common time range options:**
- `now-1h` = Last 1 hour
- `now-24h` or `now-1d` = Last 24 hours (today)
- From = `now-48h`or`now-2d` or To = `now-24h`or``now-1d` 
- `now-7d` = Last 7 days (last week)
