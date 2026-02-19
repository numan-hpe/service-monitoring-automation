import asyncio
from datetime import datetime
from collections import Counter
from login_automation import HumioLoginAutomation
from dashboard_type1 import DashboardType1Automation
from dashboard_type2 import DashboardType2Automation
from dashboard_type3 import DashboardType3Automation
from dashboard_type4 import DashboardType4Automation
from config import HUMIO_DASHBOARD_URLS, HUMIO_ENV_DISPLAY_NAMES, HUMIO_DASHBOARD_DISPLAY_NAMES

# Use dashboard URLs directly (time ranges already embedded)
DASHBOARD_URLS = HUMIO_DASHBOARD_URLS

DASHBOARD_AUTOMATION = {
    "dashboard_type_1": DashboardType1Automation,
    "dashboard_type_2": DashboardType2Automation,
    "dashboard_type_3": DashboardType3Automation,
    "dashboard_type_4": DashboardType4Automation,
}

async def run_all_environments_comprehensive_report_with_context(shared_context=None, shared_page=None, report_dir="summary reports"):
    """Run Humio automation using optional shared browser context"""
    env_display_names = HUMIO_ENV_DISPLAY_NAMES
    all_results = {}
    print(f"\n{'='*70}")
    print("COMPREHENSIVE HUMIO AUTOMATION REPORT")
    print(f"{'='*70}\n")
    
    # Setup login if no shared context provided
    if not shared_context:
        print("Initializing browser session...")
        first_dashboard_url = DASHBOARD_URLS["env1"]["dashboard_type_1"]
        login_automation = HumioLoginAutomation(dashboard_url=first_dashboard_url)
        success = await login_automation.run()
        if not success:
            print("Login failed")
            return None
        shared_context = login_automation.context
        shared_page = login_automation.page
        owns_browser = True
    else:
        print("Using shared browser context")
        owns_browser = False
        login_automation = None
    
    try:
        page = shared_page
        success = True
        
        if success:
            for env_key in ["env1", "env2", "env3", "env4"]:
                env_display = env_display_names[env_key]
                print(f"\n{'='*70}")
                print(f"Processing {env_display} ({env_key})")
                print(f"{'='*70}")
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
                                print(f"\n[{env_display}] Navigating to {dashboard_name}...")
                                await page.goto(dashboard_url, wait_until="networkidle")
                                await page.wait_for_load_state("networkidle")
                                await page.wait_for_timeout(2000)
                                print(f"[{env_display}] Navigation completed")
                            else:
                                print(f"\n[{env_display}] Already on {dashboard_name}")

                            print(f"[{env_display}] Running checks for {dashboard_name}...")
                            automation_class = DASHBOARD_AUTOMATION[dashboard_type]
                            if dashboard_type == "dashboard_type_4":
                                dashboard_automation = automation_class(page, environment=env_key)
                            else:
                                dashboard_automation = automation_class(page)
                            await dashboard_automation.run_checks()
                            env_results[dashboard_type] = dashboard_automation
                            print(f"[{env_display}] Checks completed for {dashboard_name}")
                        except Exception as e:
                            print(f"[{env_display}] Error processing {dashboard_name}: {e}")
                            env_results[dashboard_type] = f"Error: {str(e)}"
                            continue
                    all_results[env_display] = env_results
                except Exception as e:
                    print(f"[{env_display}] Critical error: {e}")
                    import traceback
                    traceback.print_exc()
                    all_results[env_display] = {"status": "FAILED", "error": str(e)}
                    continue

    finally:
        print(f"\n{'='*70}")
        print("Closing browser session...")
        if owns_browser and login_automation:
            try:
                login_automation.keep_open = False
                await login_automation.cleanup()
                print("Browser closed")
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")
        elif not owns_browser:
            print("Keeping shared browser open (managed by parent)")
        else:
            print("No browser cleanup needed (using shared context)")

    def _ordinal(n: int) -> str:
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def _extract_main_error(error_text):
        """Extract only the main error message, removing IDs and identifiers for better grouping"""
        import re
        
        # Remove leading dashes/brackets and spaces (e.g., "- - ", "- ", or "] ")
        error_text = re.sub(r'^[\]\-\s]+', '', error_text)
        
        # Remove any existing "occurred X time(s)" patterns from the error text itself
        error_text = re.sub(r'\s*-\s*occurred\s+\d+\s+times?\s*', ' ', error_text, flags=re.IGNORECASE)
        
        # Remove leading IDs and timestamps (hex strings, UUIDs, timestamps)
        error_text = re.sub(r'^(?:[a-f0-9]{16,}\s+){1,3}', '', error_text)
        error_text = re.sub(r'^[a-f0-9-]{30,}\s+', '', error_text)
        
        # Remove file paths and line numbers
        error_text = re.sub(r'^[\w.]+:\d+\s+', '', error_text)
        
        # Strip device IDs, serial numbers, and common identifiers
        # Remove device serial numbers like SGH423F5BX, CZUD3T00LP, etc.
        error_text = re.sub(r'\b[A-Z0-9]{8,12}\b', '[DEVICE_ID]', error_text)
        
        # Remove UUIDs (8-4-4-4-12 format)
        error_text = re.sub(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', '[UUID]', error_text, flags=re.IGNORECASE)
        
        # Remove pcid values like "pcid 123456"
        error_text = re.sub(r'\bpcid\s+[a-zA-Z0-9]+', 'pcid [ID]', error_text, flags=re.IGNORECASE)
        
        # Remove "for device [ID]" patterns
        error_text = re.sub(r'\bfor device\s+\[DEVICE_ID\]', 'for device', error_text, flags=re.IGNORECASE)
        error_text = re.sub(r'\bfor device:\s*\[DEVICE_ID\]', 'for device', error_text, flags=re.IGNORECASE)
        
        # Remove "device: [ID]" at end
        error_text = re.sub(r'\bdevice:\s*\[DEVICE_ID\]\s*$', 'device', error_text, flags=re.IGNORECASE)
        
        # Remove IP addresses and ports
        error_text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b', '[IP]', error_text)
        
        # Remove AWS/Kafka node addresses
        error_text = re.sub(r'\bb-\d+\.[\w.-]+\.amazonaws\.com(:\d+)?\b', '[KAFKA_NODE]', error_text)
        
        # Remove "Connection at [address]" patterns
        error_text = re.sub(r'Connection at\s+\[(?:IP|KAFKA_NODE)\]', 'Connection', error_text)
        
        # Remove node numbers in "node X" patterns (keep the text but remove specific node)
        error_text = re.sub(r'\bnode\s+\d+\b', 'node [N]', error_text, flags=re.IGNORECASE)
        
        # Remove "from X:" patterns where X is a number
        error_text = re.sub(r'\bfrom\s+\d+:', 'from [N]:', error_text)
        
        # Clean up leftover colons and spaces
        error_text = re.sub(r'\s+', ' ', error_text).strip()
        error_text = re.sub(r':\s*$', '', error_text)

        # Remove leading module prefixes without line numbers
        module_prefix = re.match(r'^([A-Za-z0-9_.]+):\s+', error_text)
        if module_prefix and '.' in module_prefix.group(1):
            error_text = error_text[module_prefix.end():]
        if re.match(r'^[A-Za-z0-9_.]+$', error_text) and '.' in error_text:
            return ""
        
        # Handle specific error patterns
        if error_text.lower().startswith('template server:'):
            return error_text.split(':', 1)[1].strip()
        if 'Unhandled exception checking is_ready for module' in error_text:
            return 'Unhandled exception checking is_ready for module'
        
        # Group all "Failed fetch messages" errors together
        if 'Failed fetch messages' in error_text:
            return 'Failed fetch messages: [Connection Error]'
        
        # Simplify Heartbeat send request failed errors
        if 'Heartbeat send request failed' in error_text:
            return 'Heartbeat send request failed: KafkaConnectionError'
        
        # Simplify Error sending HeartbeatRequest/JoinGroupRequest
        if 'Error sending HeartbeatRequest' in error_text or 'Error sending JoinGroupRequest' in error_text:
            if 'HeartbeatRequest' in error_text:
                return 'Error sending HeartbeatRequest'
            else:
                return 'Error sending JoinGroupRequest'
        
        if 'Exception while unregistering device' in error_text:
            return 'Exception while unregistering device'
        if 'Malformed gateway command received' in error_text:
            return 'Malformed gateway command received'
        if 'Invalid message received from gateway' in error_text:
            return 'Invalid message received from gateway'
        if 'ws_producer_handler task exited' in error_text:
            return 'ws_producer_handler task exited for device'
        if 'Compute provision data fetch failed' in error_text:
            # Keep error code but remove device ID
            error_text = re.sub(r'for device\s+\[DEVICE_ID\]\s+and', 'for device and', error_text)
            return error_text
        if 'Create activation key failed' in error_text:
            return 'Create activation key failed for pcid'
        
        # Extract first sentence or phrase before detailed JSON/dict data
        match = re.match(r'^([^{\[]+?)(?:\s*[{\[]|\s{3,})', error_text)
        if match:
            main_part = match.group(1).strip()
            main_part = re.sub(r':\s*Connection\s*$', '', main_part)
            main_part = re.sub(r'\s+P[0-9A-Z-+]+.*$', '', main_part)
            return main_part.strip()
        
        parts = error_text.split(':')
        if len(parts) >= 2:
            if len(parts) >= 3:
                second_part = parts[1].strip()
                if (second_part.endswith(('Error', 'Exception')) or 
                    (second_part and second_part[0].isupper() and 'Error' in second_part)):
                    result = f"{parts[0].strip()}: {parts[1].strip()}"
                    if len(parts[2].strip()) < 50:
                        result += f": {parts[2].strip()}"
                    return result
            if len(parts) == 2:
                first_part = parts[0].strip()
                second_part = parts[1].strip()
                if len(first_part) < 50 and len(second_part) < 100 and len(second_part) > 5:
                    return f"{first_part}: {second_part}"
                
            if len(parts[0].strip()) < 20 and len(parts) > 2:
                return f"{parts[0].strip()}: {parts[1].strip()}"
            return parts[0].strip()
        
        if len(error_text) > 150:
            return error_text[:150].strip() + '...'
        return error_text.strip()

    def _summarize_errors(errors):
        # Summarize errors by extracting main message and counting occurrences.
        extracted_errors = [e for e in (_extract_main_error(error) for error in errors) if e]
        counter = Counter(extracted_errors)
        summarized = []
        for text, count in counter.items():
            if count > 1:
                summarized.append(f"{text} - occurred {count} times")
            else:
                # Don't add "occurred 1 time" - just show the error
                summarized.append(text)
        return summarized

    report_lines = []
    now = datetime.now()
    report_lines.append(f"{_ordinal(now.day)} {now.strftime('%B')}")
    dashboard_display_names = HUMIO_DASHBOARD_DISPLAY_NAMES
    for env_display in ["PRE-PROD", "ANE1", "EUC1", "USW2"]:
        if env_display in all_results:
            report_lines.append(f"\n{env_display}")
            env_data = all_results[env_display]
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

                            if "oae" in errors_dict and isinstance(errors_dict["oae"], list) and errors_dict["oae"]:
                                report_lines.append("  o Error Details During iLO Onboard Activation Job")
                                for error_item in _summarize_errors(errors_dict["oae"]):
                                    report_lines.append(f"    ▪ {error_item}")
                                    error_count += 1

                            if "table" in errors_dict and isinstance(errors_dict["table"], list) and errors_dict["table"]:
                                report_lines.append("  o Subscription key assignment failure details")
                                for error_item in _summarize_errors(errors_dict["table"]):
                                    report_lines.append(f"    ▪ {error_item}")
                                    error_count += 1

                            if "pin" in errors_dict and isinstance(errors_dict["pin"], list) and errors_dict["pin"]:
                                report_lines.append("  o PIN Generation Failure")
                                for error_item in _summarize_errors(errors_dict["pin"]):
                                    report_lines.append(f"    ▪ {error_item}")
                                    error_count += 1

                            if "compute" in errors_dict and isinstance(errors_dict["compute"], list) and errors_dict["compute"]:
                                report_lines.append("  o Compute Provision Failure Details")
                                for error_item in _summarize_errors(errors_dict["compute"]):
                                    report_lines.append(f"    ▪ {error_item}")
                                    error_count += 1

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
                                    report_lines.append(f"  o {widget_name}")
                                    for error in _summarize_errors(widget_errors):
                                        if widget_name == "PII Detection Count" and error.startswith("PII Detection Count - "):
                                            error = error.replace("PII Detection Count - ", "", 1)
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

    print(f"\n{'='*70}")
    print("FINAL SUMMARY REPORT")
    print(f"{'='*70}\n")
    for line in report_lines:
        print(line)
    print(f"\n{'='*70}")
    print("REPORT GENERATION COMPLETE")
    print(f"{'='*70}\n")
    
    # Save report to text file
    import os
    # Use provided report_dir or default to summary reports folder
    report_dir = report_dir if 'report_dir' in locals() else "summary reports"
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
        print(f"Created folder: {report_dir}")
    
    today_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{today_date}_humio_service_monitoring.txt"
    filepath = os.path.join(report_dir, filename)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            for line in report_lines:
                f.write(line + "\n")
        print(f"Report saved to: {filepath}")
        return all_results
    except Exception as e:
        print(f"Error saving report to file: {e}")
        return all_results

async def main():
    await run_all_environments_comprehensive_report_with_context()
    # await run_all_dashboards_in_environment(environment="env1")
    # await run_single_dashboard(environment="env4", dashboard_type="dashboard_type_4")

if __name__ == "__main__":
    asyncio.run(main())
