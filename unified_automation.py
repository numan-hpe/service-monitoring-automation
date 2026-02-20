"""
Unified Automation Script - Runs both Grafana and Humio automations in the same browser session
"""
import asyncio
import traceback
from datetime import date
import time
import os
import json
import stat
from playwright.async_api import async_playwright
import logging
import sys

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
humio_dir = os.path.join(current_dir, 'Humio-automation-playwright')

# Add current directory to path for imports
sys.path.insert(0, current_dir)
sys.path.insert(0, humio_dir)

# Import config from current directory (graphana-automation-selenium)
from config import (
    GRAPHANA_REGION_DATA,
    GRAPHANA_HEADINGS,
    HUMIO_DASHBOARD_URLS,
    HUMIO_ENV_DISPLAY_NAMES,
    HUMIO_DASHBOARD_DISPLAY_NAMES,
    USER_EMAIL,
)

# Grafana imports
from pdf_generator import generate_pdf
from playwright_utils_async import (
    login_user_async,
    close_menu_async,
    scroll_to_widget_async,
    get_value_async,
    get_table_data_async,
    take_screenshots_async,
)

# Humio imports - using new Playwright-based automation
from dashboard_automation_main import run_all_environments_comprehensive_report_with_context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedAutomation:
    """Runs both Grafana and Humio automation in the same browser session"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.graphana_outputs = {}
        self.humio_results = {}  # Store Humio results (per environment)
        self.reports_folder = None  # Will store the reports folder path
    
    async def setup_browser(self):
        """Initialize browser with shared session"""
        logger.info("Launching browser...")
        self.playwright = await async_playwright().start()
        
        browser_channel = os.getenv("BROWSER_CHANNEL", "msedge").lower()
        launch_kwargs = {
            "headless": False,
            "args": [
                "--start-maximized",
                "--disable-device-discovery",
                "--disable-popup-blocking",
                "--disable-windows-filtering-platform",
                "--disable-blink-features=AutomationControlled",
                "--allow-running-insecure-content",
                "--disable-web-resources",
            ],
        }
        if browser_channel in {"msedge", "chrome"}:
            launch_kwargs["channel"] = browser_channel

        self.browser = await self.playwright.chromium.launch(**launch_kwargs)
        self.context = await self.browser.new_context(no_viewport=True)
        self.page = await self.context.new_page()
        logger.info("Browser launched successfully")
    
    async def run_graphana_automation(self):
        """Run Grafana automation for all regions"""
        logger.info("\n" + "="*70)
        logger.info("STARTING GRAPHANA AUTOMATION")
        logger.info("="*70 + "\n")
        
        try:
            for region, url in GRAPHANA_REGION_DATA.items():
                output = {}
                
                # Clear folder contents
                if os.path.exists(region):
                    for root, dirs, files in os.walk(region, topdown=False):
                        for name in files:
                            filename = os.path.join(root, name)
                            os.chmod(filename, stat.S_IWRITE)
                            os.remove(filename)
                else:
                    os.makedirs(region, exist_ok=True)
                
                logger.info(f"Opening {region} Grafana dashboard...")
                await self.page.goto(url, wait_until="domcontentloaded")
                
                await login_user_async(self.page)
                await asyncio.sleep(5)
                
                await close_menu_async(self.page)
                
                # SLI
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["sli"])
                output["sli"] = await get_value_async(self.page, GRAPHANA_HEADINGS["sli"])
                
                # Websockets
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["websockets"])
                output["websockets"] = await get_value_async(self.page, GRAPHANA_HEADINGS["websockets"], region)
                
                # duration > 500ms
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["duration_over_500ms"])
                output["duration_over_500ms"] = await get_table_data_async(
                    self.page, region, GRAPHANA_HEADINGS["duration_over_500ms"]
                )
                
                # HTTP 5x
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["http_5x"])
                output["http_5x"] = await get_table_data_async(self.page, region, GRAPHANA_HEADINGS["http_5x"])
                
                # Pod restarts
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["pod_restarts"])
                output["pod_restarts"] = await get_table_data_async(
                    self.page, region, GRAPHANA_HEADINGS["pod_restarts"], two_cols=True
                )
                
                # Pod counts
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["pod_counts"])
                output["pod_counts"] = await get_table_data_async(
                    self.page, region, GRAPHANA_HEADINGS["pod_counts"], three_cols=True
                )
                
                # Memory utilization
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["memory"])
                output["memory"] = await get_table_data_async(
                    self.page, region, GRAPHANA_HEADINGS["memory"], two_cols=True
                )
                
                # CPU utilization
                await scroll_to_widget_async(self.page, GRAPHANA_HEADINGS["cpu"])
                output["cpu"] = await get_table_data_async(self.page, region, GRAPHANA_HEADINGS["cpu"], two_cols=True)
                
                # Screenshots
                screenshots = await take_screenshots_async(self.page, region)
                
                with open(os.path.join(region, "data.json"), "w") as json_file:
                    json.dump(output, json_file, indent=4)
                
                self.graphana_outputs[region] = output
                logger.info(f"Data collected for {region}")
            
            # Generate PDF report
            today_date = date.today().strftime("%Y-%m-%d")
            formatted_datetime = today_date + "_" + time.strftime("%H-%M")
            
            # Create date-based folder for all reports
            reports_folder = os.path.join("reports", today_date)
            os.makedirs(reports_folder, exist_ok=True)
            generate_pdf(reports_folder, f"service_monitoring_{formatted_datetime}.pdf")
            
            # Store for use in generate_humio_report
            self.reports_folder = reports_folder
            
            logger.info("\n" + "="*70)
            logger.info("GRAPHANA AUTOMATION COMPLETED SUCCESSFULLY")
            logger.info("="*70 + "\n")
            return True
            
        except Exception as e:
            logger.error(f"Error in Grafana automation: {traceback.format_exc()}")
            return False
    
    async def run_all_humio_environments(self):
        """Run Humio automation for all environments using new Playwright-based automation"""
        logger.info("\n" + "="*70)
        logger.info("STARTING HUMIO AUTOMATION FOR ALL ENVIRONMENTS")
        logger.info("="*70 + "\n")
        
        try:
            # Determine report directory based on whether Grafana ran
            if hasattr(self, 'reports_folder') and self.reports_folder:
                report_dir = self.reports_folder
                logger.info(f"Using Grafana reports folder: {report_dir}")
            else:
                # Create standalone reports folder with timestamp
                today_date = date.today().strftime("%Y-%m-%d")
                report_dir = os.path.join("reports", today_date)
                os.makedirs(report_dir, exist_ok=True)
                logger.info(f"Created reports folder: {report_dir}")
            
            # If running standalone (no shared context), we need to handle login
            if not hasattr(self, 'context') or self.context is None or not hasattr(self, 'page') or self.page is None:
                logger.info("No shared browser context - Humio automation will handle login")
                self.humio_results = await run_all_environments_comprehensive_report_with_context(
                    shared_context=None,
                    shared_page=None,
                    report_dir=report_dir
                )
            else:
                logger.info("Using shared browser context from Grafana")
                # Run the new Playwright-based Humio automation with shared browser context
                self.humio_results = await run_all_environments_comprehensive_report_with_context(
                    shared_context=self.context,
                    shared_page=self.page,
                    report_dir=report_dir
                )
            
            if self.humio_results:
                logger.info("\n" + "="*70)
                logger.info("HUMIO AUTOMATION COMPLETED SUCCESSFULLY")
                logger.info("="*70 + "\n")
                return True
            else:
                logger.error("Humio automation returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Error in Humio automation: {traceback.format_exc()}")
            return False
    
    def generate_humio_report(self):
        """Generate Humio report with the exact original structure."""
        from datetime import datetime
        from collections import Counter

        def _ordinal(n: int) -> str:
            if 10 <= n % 100 <= 20:
                suffix = "th"
            else:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
            return f"{n}{suffix}"

        def _extract_main_error(error_text):
            import re
            error_text = re.sub(r'^[\]\-\s]+', '', error_text)
            
            # Remove any existing "occurred X time(s)" patterns from the error text
            error_text = re.sub(r'\s*-\s*occurred\s+\d+\s+times?\s*', ' ', error_text, flags=re.IGNORECASE)
            
            error_text = re.sub(r'^(?:[a-f0-9]{16,}\s+){1,3}', '', error_text)
            error_text = re.sub(r'^[a-f0-9-]{30,}\s+', '', error_text)
            error_text = re.sub(r'^[\w.]+:\d+\s+', '', error_text)
            
            # Special handling for "Compute provision data fetch failed" - strip device ID and error code
            if 'Compute provision data fetch failed' in error_text:
                return 'Compute provision data fetch failed for device'
            
            # Special handling for "Failed fetch messages from X:" - strip the number and connection details
            if 'Failed fetch messages from' in error_text:
                # Strip node number and connection details, keep just the error type
                error_text = re.sub(r'from\s+\d+:.*?(?=\s|$)', 'from:', error_text)
                error_text = re.sub(r':\s*Connection at.*', '', error_text)
                return error_text.strip()

            module_prefix = re.match(r'^([A-Za-z0-9_.]+):\s+', error_text)
            if module_prefix and '.' in module_prefix.group(1):
                error_text = error_text[module_prefix.end():]
            if re.match(r'^[A-Za-z0-9_.]+$', error_text) and '.' in error_text:
                return ""
            if error_text.lower().startswith('template server:'):
                return error_text.split(':', 1)[1].strip()
            if 'Unhandled exception checking is_ready for module' in error_text:
                return error_text.strip()
            match = re.search(r'(Failed fetch messages from \d+: \w+(?:Error)?)', error_text)
            if match:
                return match.group(1)
            if 'Exception while unregistering device' in error_text:
                return 'Exception while unregistering device'
            if 'Malformed gateway command received' in error_text:
                return 'Malformed gateway command received'

            match = re.match(r'^([^\[{]+?)(?:\s*[\[{]|\s{3,})', error_text)
            if match:
                main_part = match.group(1).strip()
                main_part = re.sub(r':\s*Connection at.*$', '', main_part)
                main_part = re.sub(r':\s*[a-z0-9.-]+:\d+.*$', '', main_part, flags=re.IGNORECASE)
                main_part = re.sub(r'\s+P[0-9A-Z-+]+.*$', '', main_part)
                return main_part.strip()

            parts = error_text.split(':')
            if len(parts) >= 2:
                if len(parts) >= 3:
                    second_part = parts[1].strip()
                    if (second_part.endswith(('Error', 'Exception')) or
                        (second_part and second_part[0].isupper() and 'Error' in second_part)):
                        return f"{parts[0].strip()}: {parts[1].strip()}: {parts[2].strip()}"
                if len(parts) == 2:
                    first_part = parts[0].strip()
                    second_part = parts[1].strip()
                    if len(first_part) < 50 and len(second_part) < 100 and len(second_part) > 5:
                        if not re.search(r'[a-z0-9.-]+:\d+', second_part, re.IGNORECASE):
                            return f"{first_part}: {second_part}"

                if len(parts[0].strip()) < 20 and len(parts) > 2:
                    return f"{parts[0].strip()}: {parts[1].strip()}"
                return parts[0].strip()

            if len(error_text) > 150:
                return error_text[:150].strip() + '...'
            return error_text.strip()

        def _summarize_errors(errors):
            extracted_errors = [e for e in (_extract_main_error(error) for error in errors) if e]
            counter = Counter(extracted_errors)
            summarized = []
            for text, count in counter.items():
                if count > 1:
                    summarized.append(f"{text} - occurred {count} times")
                else:
                    summarized.append(text)  # Just show error without "occurred 1 time"
            return summarized

        report_lines = []
        now = datetime.now()
        report_lines.append(f"{_ordinal(now.day)} {now.strftime('%B')}")

        dashboard_display_names = HUMIO_DASHBOARD_DISPLAY_NAMES
        for env_display in ["PRE-PROD", "ANE1", "EUC1", "USW2"]:
            if env_display in self.humio_results:
                report_lines.append(f"\n{env_display}")
                env_data = self.humio_results[env_display]
                if isinstance(env_data, dict) and env_data.get("status") in ["LOGIN_FAILED", "FAILED"]:
                    report_lines.append(f"✗ {env_data.get('error', 'Failed')}")
                    continue
                dashboard_order = ["dashboard_type_2", "dashboard_type_1", "dashboard_type_3", "dashboard_type_4"]
                for db_type in dashboard_order:
                    if db_type in env_data:
                        db_display = dashboard_display_names[db_type]
                        report_lines.append(f"• {db_display}")
                        dashboard_obj = env_data[db_type]
                        if db_type == "dashboard_type_3":
                            if hasattr(dashboard_obj, "errors_dict") and dashboard_obj.errors_dict:
                                errors_dict = dashboard_obj.errors_dict
                                error_count = 0

                                # Error Details During iLO Onboard Activation Job
                                if "oae" in errors_dict:
                                    report_lines.append("  o Error Details During iLO Onboard Activation Job")
                                    if isinstance(errors_dict["oae"], list) and errors_dict["oae"]:
                                        for error_item in _summarize_errors(errors_dict["oae"]):
                                            report_lines.append(f"    ▪ {error_item}")
                                            error_count += 1
                                    # Note: if oae exists but is empty, heading is shown but no errors listed

                                # Subscription key assignment failure details
                                if "table" in errors_dict and isinstance(errors_dict["table"], list) and errors_dict["table"]:
                                    report_lines.append("  o Subscription key assignment failure details")
                                    for error_item in _summarize_errors(errors_dict["table"]):
                                        report_lines.append(f"    ▪ {error_item}")
                                        error_count += 1

                                # PIN Generation Failure
                                if "pin" in errors_dict and isinstance(errors_dict["pin"], list) and errors_dict["pin"]:
                                    report_lines.append("  o PIN Generation Failure")
                                    for error_item in _summarize_errors(errors_dict["pin"]):
                                        report_lines.append(f"    ▪ {error_item}")
                                        error_count += 1

                                # Compute Provision Failure Details
                                if "compute" in errors_dict:
                                    report_lines.append("  o Compute Provision Failure Details")
                                    if isinstance(errors_dict["compute"], list) and errors_dict["compute"]:
                                        for error_item in _summarize_errors(errors_dict["compute"]):
                                            report_lines.append(f"    ▪ {error_item}")
                                            error_count += 1
                                    # Note: if compute exists but is empty, heading is shown but no errors listed

                                if "jwt" in errors_dict:
                                    report_lines.append(f"  o JWT generation failed - {errors_dict['jwt']}")
                                    error_count += 1
                                if "subscription" in errors_dict:
                                    report_lines.append(f"  o Subscription Key Claim Failure - {errors_dict['subscription']}")
                                    error_count += 1
                                if "device" in errors_dict:
                                    report_lines.append(f"  o Device not available GLP Pool - {errors_dict['device']}")
                                    error_count += 1
                                if "location" in errors_dict:
                                    report_lines.append(f"  o Location/Tags/Sdc Patch Failure - {errors_dict['location']}")
                                    error_count += 1
                                if error_count == 0:
                                    report_lines.append("  o No errors")
                            else:
                                report_lines.append("  o No errors")

                        elif db_type == "dashboard_type_4":
                            if hasattr(dashboard_obj, "widgets") and dashboard_obj.widgets:
                                for widget_data in dashboard_obj.widgets:
                                    widget_name = widget_data.get("name", "Unknown Widget")
                                    widget_errors = widget_data.get("errors", [])
                                    if widget_errors and isinstance(widget_errors, list):
                                        # Special handling for PII Detection Count
                                        if widget_name == "PII Detection Count":
                                            # Check if the only error is "0"
                                            summarized = _summarize_errors(widget_errors)
                                            if len(summarized) == 1 and summarized[0].strip() in ["0", "PII Detection Count - 0"]:
                                                report_lines.append(f"  o {widget_name} - No errors")
                                            else:
                                                report_lines.append(f"  o {widget_name}")
                                                for error in summarized:
                                                    if error.startswith("PII Detection Count - "):
                                                        error = error.replace("PII Detection Count - ", "", 1)
                                                    report_lines.append(f"    ▪ {error}")
                                        else:
                                            report_lines.append(f"  o {widget_name}")
                                            for error in _summarize_errors(widget_errors):
                                                report_lines.append(f"    ▪ {error}")
                                    else:
                                        report_lines.append(f"  o {widget_name} - No errors")
                            else:
                                report_lines.append("  o No widget data available")

                        else:
                            if hasattr(dashboard_obj, "result"):
                                result = dashboard_obj.result
                                if "No errors" in result:
                                    report_lines.append("  o No errors")
                                elif " - " in result:
                                    parts = result.split(" - ", 1)
                                    if len(parts) > 1:
                                        errors = parts[1].split(" | ")
                                        for error in errors:
                                            error_clean = error.strip()
                                            if error_clean:
                                                report_lines.append(f"  o {error_clean}")
                                else:
                                    report_lines.append("  o No data")
                            else:
                                report_lines.append("  o No data")

        # Use the same date-based folder as Grafana report
        today_date_folder = datetime.now().strftime("%Y-%m-%d")
        folder_name = os.path.join("reports", today_date_folder)
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        today_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{today_date}_humio_service_monitoring.txt"
        filepath = os.path.join(folder_name, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            for line in report_lines:
                f.write(line + "\n")

        # Print report to terminal
        logger.info("\n" + "="*70)
        logger.info("HUMIO SERVICE MONITORING REPORT")
        logger.info("="*70)
        for line in report_lines:
            logger.info(line)
        logger.info("="*70)
        logger.info(f"Report saved to: {filepath}")
        logger.info("="*70 + "\n")
        
        return filepath
    
    async def run_all(self):
        """Run both Grafana and Humio automation in sequence"""
        humio_report_path = None
        try:
            # Setup browser
            await self.setup_browser()
            
            # Run Grafana automation
            graphana_success = await self.run_graphana_automation()
            
            if not graphana_success:
                logger.error("Grafana automation failed. Stopping.")
                return False
            
            # Run Humio automation for all environments
            humio_success = await self.run_all_humio_environments()
            
            if not humio_success:
                logger.error("Some Humio automations failed.")
                # Continue anyway to show results
            
            logger.info("\n" + "="*70)
            logger.info("ALL AUTOMATIONS COMPLETED!")
            logger.info("="*70 + "\n")
            
            # Generate Humio report (original structure)
            logger.info("Generating Humio report...")
            humio_report_path = self.generate_humio_report()
            logger.info(f"Humio report saved: {humio_report_path}\n")
            
            # Ask user if they want to close the browser
            logger.info("Browser will remain open for 30 seconds for inspection...")
            logger.info("You can review the results in the browser.")
            await asyncio.sleep(30)
            
            # Close browser
            logger.info("\nClosing browser...")
            await self.cleanup()
            logger.info("Browser closed successfully")
            
            logger.info("\n" + "="*70)
            logger.info("AUTOMATION COMPLETED - ALL TASKS FINISHED!")
            logger.info("="*70 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in unified automation: {traceback.format_exc()}")
            return False
        finally:
            # Ensure report and cleanup even if errors occurred
            if humio_report_path is None:
                try:
                    logger.info("Generating Humio report (finalizer)...")
                    humio_report_path = self.generate_humio_report()
                    logger.info(f"Humio report saved: {humio_report_path}\n")
                except Exception as report_error:
                    logger.error(f"Failed to generate Humio report: {report_error}")
            try:
                logger.info("Final cleanup: closing browser...")
                await self.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Final cleanup error: {cleanup_error}")
    
    async def cleanup(self):
        """Close browser and cleanup"""
        try:
            if self.context:
                await asyncio.wait_for(self.context.close(), timeout=10)
            if self.browser:
                await asyncio.wait_for(self.browser.close(), timeout=10)
            if self.playwright:
                await asyncio.wait_for(self.playwright.stop(), timeout=10)
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Entry point"""
    automation = UnifiedAutomation()
    success = await automation.run_all()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
