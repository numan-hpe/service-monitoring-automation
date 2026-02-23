import asyncio
from datetime import datetime
from collections import Counter
from login_automation import HumioLoginAutomation
from dashboard_type1 import DashboardType1Automation
from dashboard_type2 import DashboardType2Automation
from dashboard_type3 import DashboardType3Automation
from dashboard_type4 import DashboardType4Automation
from config import HUMIO_DASHBOARD_URLS, HUMIO_ENV_DISPLAY_NAMES, HUMIO_DASHBOARD_DISPLAY_NAMES

# Import shared error utilities
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from error_utils import _ordinal, _extract_main_error, _summarize_errors
from report_generator import HumioReportGenerator

# Use dashboard URLs directly (time ranges already embedded)
DASHBOARD_URLS = HUMIO_DASHBOARD_URLS

DASHBOARD_AUTOMATION = {
    "dashboard_type_1": DashboardType1Automation,
    "dashboard_type_2": DashboardType2Automation,
    "dashboard_type_3": DashboardType3Automation,
    "dashboard_type_4": DashboardType4Automation,
}

async def run_all_environments_comprehensive_report_with_context(shared_context=None, shared_page=None, report_dir="summary reports"):
    #Run Humio automation using optional shared browser context.
    env_display_names = HUMIO_ENV_DISPLAY_NAMES
    all_results = {}
    
    # Setup login if no shared context provided
    if not shared_context:
        print("Initializing Humio browser session...")
        first_dashboard_url = DASHBOARD_URLS["env1"]["dashboard_type_1"]
        login_automation = HumioLoginAutomation(dashboard_url=first_dashboard_url)
        success = await login_automation.run()
        if not success:
            print("ERROR: Login failed")
            return None
        shared_context = login_automation.context
        shared_page = login_automation.page
        owns_browser = True
    else:
        owns_browser = False
        login_automation = None
    
    try:
        page = shared_page
        success = True
        
        if success:
            for env_key in ["env1", "env2", "env3", "env4"]:
                env_display = env_display_names[env_key]
                print(f"Processing {env_display}...")
                dashboard_urls = DASHBOARD_URLS[env_key]
                env_results = {}
                try:
                    dashboard_list = list(dashboard_urls.items())
                    for idx, (dashboard_type, dashboard_url) in enumerate(dashboard_list):
                        dashboard_name = {
                            "dashboard_type_1": "Data Ingestion",
                            "dashboard_type_2": "COM Subscription",
                            "dashboard_type_3": "Activation Keys",
                            "dashboard_type_4": "Service-Errors",
                        }.get(dashboard_type, dashboard_type)
                        try:
                            if not (env_key == "env1" and idx == 0):
                                await page.goto(dashboard_url, wait_until="networkidle")
                                await page.wait_for_load_state("networkidle")
                                await page.wait_for_timeout(2000)
                            
                            automation_class = DASHBOARD_AUTOMATION[dashboard_type]
                            if dashboard_type == "dashboard_type_4":
                                dashboard_automation = automation_class(page, environment=env_key)
                            else:
                                dashboard_automation = automation_class(page)
                            await dashboard_automation.run_checks()
                            env_results[dashboard_type] = dashboard_automation
                        except Exception as e:
                            print(f"ERROR [{env_display}] {dashboard_name}: {e}")
                            env_results[dashboard_type] = f"Error: {str(e)}"
                            continue
                    all_results[env_display] = env_results
                except Exception as e:
                    print(f"ERROR [{env_display}] Critical error: {e}")
                    all_results[env_display] = {"status": "FAILED", "error": str(e)}
                    continue

    finally:
        if owns_browser and login_automation:
            try:
                login_automation.keep_open = False
                await login_automation.cleanup()
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")

    report_lines = HumioReportGenerator.generate_report(all_results)
    
    return all_results, report_lines

async def main():
    await run_all_environments_comprehensive_report_with_context()
    # await run_all_dashboards_in_environment(environment="env1")
    # await run_single_dashboard(environment="env4", dashboard_type="dashboard_type_4")

if __name__ == "__main__":
    asyncio.run(main())
