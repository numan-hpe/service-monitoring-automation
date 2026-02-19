USER_EMAIL = "deeksha.jayanth@hpe.com"
BOT_TOKEN = "Add token here"
CHANNEL_ID = "C085P82Q4R4"

# Grafana time range parameters (defaults to last 24 hours from now)
# Examples:
#   "now-24h"  = Last 24 hours from now (today)
#   "now-7d"   = Last 7 days from now (last week)
#   "now-48h"  = Last 48 hours from now (last 2 days)
#   "now-1h"   = Last 1 hour from now
#   "now"      = Current time
GRAPHANA_FROM = "now-24h"
GRAPHANA_TO = "now"
GRAPHANA_TIMEZONE = "IST"

# Shared auth session (Selenium -> Playwright)
# Note: session cookies are currently not used by the unified Playwright flow.
SESSION_COOKIES_PATH = "session_cookies.json"

# Time range parameters for Grafana and Humio (defaults to last 24 hours from now - today)
# Examples:
#   "now-1d"   = Last 1 day from now (today) - DEFAULT
#   "now-7d"   = Last 7 days from now (last week)
#   "now-2d"   = Last 2 days from now (today + yesterday)
#   "now-96h"  = Last 96 hours from now (4 days)
#   "now-15m"  = Last 15 minutes from now
#   "now"      = Current time
HUMIO_FROM = "now-1d"
HUMIO_TO = "now"

def _convert_humio_time(time_str):
    """Convert now-2d/now-96h/now-15m to Humio format (2days/96hours/15minutes)."""
    import re
    if time_str == "now":
        return "now"
    match = re.match(r"now-(\d+)([dhm])", time_str)
    if match:
        value, unit = match.groups()
        unit_map = {"d": "days", "h": "hours", "m": "minutes"}
        return f"{value}{unit_map.get(unit, 'days')}"
    return time_str

_HUMIO_FROM_CONVERTED = _convert_humio_time(HUMIO_FROM)
_HUMIO_TO_CONVERTED = _convert_humio_time(HUMIO_TO)

# GRAPHANA CONFIGURATION
SERVICES = ["keysmith", "charger", "charger-delta", "zinc-app", "roundup", "neptune"]

def get_services_string(region):
    services = [
        f"var-rugbyservice={region}-{service}"
        for service in SERVICES
    ]
    return "&".join(services)

GRAPHANA_REGION_DATA = {
    "ccprodusw2": f"https://ccprodusw2-us-west-2.cloudops.compute.cloud.hpe.com/tenant-monitoring/d/uid_chk_eng_lght/rugby-daily-check-engine-light?orgId=1&from={GRAPHANA_FROM}&to={GRAPHANA_TO}&timezone={GRAPHANA_TIMEZONE}&" + get_services_string("ccprodusw2"),
    "ccprodeuc1": f"https://ccprodeuc1-eu-central-1.cloudops.compute.cloud.hpe.com/tenant-monitoring/d/uid_chk_eng_lght/rugby-daily-check-engine-light?orgId=1&from={GRAPHANA_FROM}&to={GRAPHANA_TO}&timezone={GRAPHANA_TIMEZONE}&" + get_services_string("ccprodeuc1"),
    "ccprodane1": f"https://ccprodane1-ap-northeast-1.cloudops.compute.cloud.hpe.com/tenant-monitoring/d/uid_chk_eng_lght/rugby-daily-check-engine-light?orgId=1&from={GRAPHANA_FROM}&to={GRAPHANA_TO}&timezone={GRAPHANA_TIMEZONE}&" + get_services_string("ccprodane1"),
    "pre-prod": f"https://ccpreusw2-us-west-2.cloudops.compute.cloud.hpe.com/tenant-monitoring/d/uid_chk_eng_lght/rugby-daily-check-engine-light?orgId=1&from={GRAPHANA_FROM}&to={GRAPHANA_TO}&timezone={GRAPHANA_TIMEZONE}&" + get_services_string("pre-prod"),
}

GRAPHANA_HEADINGS = {
    "sli": "Latency, Error-Rate, Availability Combined",
    "websockets": "Number of --currently connected-- websocket connections",
    "duration_over_500ms": "Durations > 500ms  (Click Data Points for more info)",
    # "duration_over_500ms_special": "Durations > 500ms  - Special Cases   (Click Data Points for more info)",
    "http_5x": "HTTP 5x responses",
    "pod_restarts": "Pod Restarts",
    "pod_counts": "Pod Counts over time",
    "memory": "Namespace relative memory utilization",
    "cpu": "Namespace relative CPU utilization",
}
SCREENSHOT_DATA = {
    "websockets": {"type": "small", "heading": "Websocket Connections"},
    "cpu": {"type": "large", "heading": GRAPHANA_HEADINGS["cpu"]},
    "memory": {"type": "large", "heading": GRAPHANA_HEADINGS["memory"]},
}

# Backward compatibility aliases
REGION_DATA = GRAPHANA_REGION_DATA
HEADINGS = GRAPHANA_HEADINGS

# HUMIO CONFIGURATION - with IST timezone (Asia/Calcutta)
HUMIO_DASHBOARD_URLS = {
    "env1": {
        "dashboard_type_1": f"https://ccpreusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Data%20Ingestion%20to%20Sustainability%20Insight%20Center?dashboardId=c1aViyZqkRvBsI3eMKRpOQ6zCzPWJ35z&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_2": f"https://ccpreusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/COM%20Subscription%20and%20Consumption?dashboardId=EJp6d928ejsSA00kw2emoBhcVNf2OjOd&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_3": f"https://ccpreusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Activation%20Key%20Onboarding?dashboardId=LtFA33nlpz73ZpH9608jqRLQBlvpbnPz&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_4": f"https://ccpreusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/%5BTS-Manisha%5D%20Service-Errors%20Filter%20Known%20Issues%20(pre-prod)?dashboardId=UCTmt1Oxn5PhLs1ReaqS1lqpyZd8a3is&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
    },
    "env2": {
        "dashboard_type_1": f"https://ccprodane1-ap-northeast-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Data%20Ingestion%20to%20Sustainability%20Insight%20Center?dashboardId=8baepYQQfzBT8JBf1d3T51niNeKAhmeQ&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_2": f"https://ccprodane1-ap-northeast-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/COM%20Subscription%20and%20Consumption?dashboardId=BjjaphcXKAExfBqVX5WbMjnI79hO8oDd&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_3": f"https://ccprodane1-ap-northeast-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Activation%20Key%20Onboarding?dashboardId=8vglYJMqNn8w7piqx8JjaPsbgINTsyvM&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_4": f"https://ccprodane1-ap-northeast-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/%5BTS-Manisha%5D%20Service-Errors%20Filter%20Known%20Issues?dashboardId=4CgWG7CJ2siNnxNsQjMvmsrySaaBXh6o&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
    },
    "env3": {
        "dashboard_type_1": f"https://ccprodeuc1-eu-central-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Data%20Ingestion%20to%20Sustainability%20Insight%20Center?dashboardId=CXyM0Ixx13oKBIu4qdVSouvNr3z72Q7R&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_2": f"https://ccprodeuc1-eu-central-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/COM%20Subscription%20and%20Consumption?dashboardId=7HOpZefQ7ATnthap8qOzG4ce5mq4tsSF&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_3": f"https://ccprodeuc1-eu-central-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Activation%20Key%20Onboarding?dashboardId=2sU9buDIfWraWyqToP7tlvwL6CfIGuz8&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_4": f"https://ccprodeuc1-eu-central-1.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/%5BTS-Manisha%5D%20Service-Errors%20Filter%20Known%20Issues?dashboardId=MEKx3SLFhPj8TTDZHVug9a5Vq6vo2MvG&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
    },
    "env4": {
        "dashboard_type_1": f"https://ccprodusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Data%20Ingestion%20to%20Sustainability%20Insight%20Center?dashboardId=k1IfQQ0CrPmymhHWIQhVVOGX9iP8F9WE&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_2": f"https://ccprodusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/COM%20Subscription%20and%20Consumption?dashboardId=PrsSt0o2jnyVDfUtF6G5RuW8J0B04hFE&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_3": f"https://ccprodusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/Activation%20Key%20Onboarding?dashboardId=8CtZeTHokVjo0k24Hw498lhqgHJNAnyf&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
        "dashboard_type_4": f"https://ccprodusw2-us-west-2.cloudops.compute.cloud.hpe.com/logs/computecentral/dashboards/%5BTS-Manisha%5D%20Service-Errors%20Filter%20Known%20Issues?dashboardId=UNUXGptMYR0BzrmRpEqA8NiOPQzXUqM9&start={_HUMIO_FROM_CONVERTED}&end={_HUMIO_TO_CONVERTED}&tz=Asia%2FCalcutta",
    },
}

HUMIO_ENV_DISPLAY_NAMES = {
    "env1": "PRE-PROD",
    "env2": "ANE1",
    "env3": "EUC1",
    "env4": "USW2",
}

HUMIO_DASHBOARD_DISPLAY_NAMES = {
    "dashboard_type_1": "Data Ingestion to Sustainability Insight Center",
    "dashboard_type_2": "COM Subscription And Consumption",
    "dashboard_type_3": "Activation Keys Onboarding",
    "dashboard_type_4": "Service-Errors Filter Known Issues",
}

HUMIO_HEADINGS = {
    "files_failures": "Files failed to upload",
    "unknown_errors": "Unknown Error during server_metric_data message processing",
    "bisbee_errors": "Exception while uploading file to bisbee",
}
