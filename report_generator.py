import os
from datetime import datetime
from error_utils import _ordinal, _summarize_errors
from config import HUMIO_DASHBOARD_DISPLAY_NAMES

class HumioReportGenerator:
    
    @staticmethod
    def generate_report(all_results):
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
                
                # Process dashboards in order
                dashboard_order = ["dashboard_type_2", "dashboard_type_1", "dashboard_type_3", "dashboard_type_4"]
                for db_type in dashboard_order:
                    if db_type in env_data:
                        db_display = dashboard_display_names[db_type]
                        report_lines.append(f"• {db_display}")
                        dashboard_obj = env_data[db_type]
                        if db_type == "dashboard_type_3":
                            HumioReportGenerator._format_dashboard_type_3(
                                dashboard_obj, report_lines
                            )
                        elif db_type == "dashboard_type_4":
                            HumioReportGenerator._format_dashboard_type_4(
                                dashboard_obj, report_lines
                            )
                        else:
                            HumioReportGenerator._format_generic_dashboard(
                                dashboard_obj, report_lines
                            )  
        return report_lines
    
    @staticmethod
    def _format_dashboard_type_3(dashboard_obj, report_lines):
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
            
            # Additional error fields
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
    
    @staticmethod
    def _format_dashboard_type_4(dashboard_obj, report_lines):
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
    
    @staticmethod
    def _format_generic_dashboard(dashboard_obj, report_lines):
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
    
    @staticmethod
    def save_report(report_lines, report_dir="reports", print_output=True):
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        today_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{today_date}_humio_service_monitoring.txt"
        filepath = os.path.join(report_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for line in report_lines:
                    f.write(line + "\n")
            
            if print_output:
                print(f"\n{'='*70}")
                print("HUMIO AUTOMATION REPORT SUMMARY")
                print(f"{'='*70}\n")
                for line in report_lines:
                    print(line)
                print(f"\n{'='*70}\n")
                print(f"Report saved: {filepath}")
            
            return filepath
        except Exception as e:
            print(f"ERROR: Failed to save report: {e}")
            return None
