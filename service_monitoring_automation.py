import asyncio
import sys
import argparse
import os

# Ensure UTF-8 encoding for proper Unicode character display on Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Centralize Python cache to root .pycache directory
project_root = os.path.dirname(os.path.abspath(__file__))
os.environ['PYTHONPYCACHEPREFIX'] = os.path.join(project_root, '.pycache')


async def run_unified_automation(mode="all"):
    """
    Run automation based on mode:
    - "all" (default): Run both Grafana and Humio
    - "graphana": Run only Grafana
    - "humio": Run only Humio
    """
    from unified_automation import UnifiedAutomation
    
    if mode == "all":
        print("\n=== Starting Unified Automation (Grafana + Humio) ===")
        automation = UnifiedAutomation()
        success = await automation.run_all()
        
    elif mode == "graphana":
        print("\n=== Starting Grafana Automation Only ===")
        automation = UnifiedAutomation()
        try:
            await automation.setup_browser()
            success = await automation.run_graphana_automation()
            print("\n" + "="*70)
            if success:
                print("GRAPHANA AUTOMATION COMPLETED SUCCESSFULLY")
            else:
                print("GRAPHANA AUTOMATION FAILED")
            print("="*70 + "\n")
        except Exception as e:
            print(f"Error: {e}")
            success = False
        finally:
            try:
                await automation.cleanup()
            except:
                pass
                
    elif mode == "humio":
        print("\n=== Starting Humio Automation Only ===")
        automation = UnifiedAutomation()
        try:
            # Don't call setup_browser() for humio only mode
            # Let the humio automation create its own browser and handle login
            success = await automation.run_all_humio_environments()
            
            if success:
                # Generate report from Humio results
                from report_generator import HumioReportGenerator
                from datetime import date
                import os
                
                report_lines = HumioReportGenerator.generate_report(automation.humio_results)
                today_date = date.today().strftime("%Y-%m-%d")
                report_dir = os.path.join("reports", today_date)
                os.makedirs(report_dir, exist_ok=True)
                
                filepath = HumioReportGenerator.save_report(report_lines, report_dir, print_output=True)
                
                print("\n" + "="*70)
                print("HUMIO AUTOMATION COMPLETED SUCCESSFULLY")
                if filepath:
                    print(f"Report saved to: {filepath}")
                print("="*70 + "\n")
            else:
                print("\n" + "="*70)
                print("HUMIO AUTOMATION FAILED")
                print("="*70 + "\n")
                success = False
        except Exception as e:
            print(f"Error: {e}")
            success = False
        finally:
            try:
                await automation.cleanup()
            except:
                pass
    else:
        print(f"Invalid mode: {mode}")
        success = False
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Monitoring Automation - Run Grafana and/or Humio automations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python service_monitoring_automation.py              # Run both Grafana and Humio (default)
    python service_monitoring_automation.py --graphana    # Run only Grafana automation
    python service_monitoring_automation.py --humio      # Run only Humio automation
        """
    )
    
    parser.add_argument(
        "--graphana",
        action="store_true",
        help="Run only Grafana automation"
    )
    parser.add_argument(
        "--humio",
        action="store_true",
        help="Run only Humio automation"
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.graphana and args.humio:
        print("Error: Cannot use both --graphana and --humio. Choose one or run without flags for both.")
        sys.exit(1)
    elif args.graphana:
        mode = "graphana"
    elif args.humio:
        mode = "humio"
    else:
        mode = "all"
    
    # Run automation
    success = asyncio.run(run_unified_automation(mode))
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
