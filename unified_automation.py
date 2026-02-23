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

current_dir = os.path.dirname(os.path.abspath(__file__))
humio_dir = os.path.join(current_dir, 'Humio-automation-playwright')

sys.path.insert(0, current_dir)
sys.path.insert(0, humio_dir)

from config import (
    GRAPHANA_REGION_DATA,
    GRAPHANA_HEADINGS,
    HUMIO_DASHBOARD_URLS,
    HUMIO_ENV_DISPLAY_NAMES,
    HUMIO_DASHBOARD_DISPLAY_NAMES,
    USER_EMAIL,
)
from error_utils import _ordinal, _extract_main_error, _summarize_errors
from report_generator import HumioReportGenerator

from pdf_generator import generate_pdf
from playwright_utils_async import (
    login_user_async,
    close_menu_async,
    scroll_to_widget_async,
    get_value_async,
    get_table_data_async,
    take_screenshots_async,
)
from dashboard_automation_main import run_all_environments_comprehensive_report_with_context

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedAutomation:    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.graphana_outputs = {}
        self.humio_results = {}  # Store Humio results (per environment)
        self.reports_folder = None  # Will store the reports folder path
    
    async def setup_browser(self):
        # Initialize browser with shared session
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
        # Run Grafana automation for all regions
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
                all_results, report_lines = await run_all_environments_comprehensive_report_with_context(
                    shared_context=None,
                    shared_page=None,
                    report_dir=report_dir
                )
            else:
                logger.info("Using shared browser context from Grafana")
                # Run the new Playwright-based Humio automation with shared browser context
                all_results, report_lines = await run_all_environments_comprehensive_report_with_context(
                    shared_context=self.context,
                    shared_page=self.page,
                    report_dir=report_dir
                )
            
            # Store results and report lines
            self.humio_results = all_results
            self.humio_report_lines = report_lines 
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
        if not hasattr(self, 'humio_report_lines'):
            logger.error("No Humio report lines available")
            return None
        
        # Determine report directory
        today_date_folder = date.today().strftime("%Y-%m-%d")
        folder_name = os.path.join("reports", today_date_folder)
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        
        # Save report
        filepath = HumioReportGenerator.save_report(
            self.humio_report_lines, 
            folder_name, 
            print_output=True
        )
        
        if filepath:
            logger.info(f"Report saved to: {filepath}")
        
        return filepath
    
    async def run_all(self):
        # Run both Grafana and Humio automation in sequence
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
    automation = UnifiedAutomation()
    success = await automation.run_all()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
