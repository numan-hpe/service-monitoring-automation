import traceback
from datetime import date
import time
import os
import json
import stat
from playwright.sync_api import sync_playwright
from pdf_generator import generate_pdf
from config import REGION_DATA, HEADINGS
from playwright_utils import (
    login_user,
    close_menu,
    scroll_to_widget,
    get_value,
    get_table_data,
    take_screenshots,
)

output = {}
REGION_OUTPUTS = {}
try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-device-discovery",
                "--disable-popup-blocking",
                "--disable-windows-filtering-platform",
                "--disable-blink-features=AutomationControlled",
                "--allow-running-insecure-content",
                "--disable-web-resources",
            ],
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        for region, url in REGION_DATA.items():
            # Clear folder contents
            if os.path.exists(region):
                for root, dirs, files in os.walk(region, topdown=False):
                    for name in files:
                        filename = os.path.join(root, name)
                        os.chmod(filename, stat.S_IWRITE)
                        os.remove(filename)
            else:
                os.makedirs(region, exist_ok=True)
            print(f"Opening {region} Grafana dashboard...")
            page.goto(url, wait_until="domcontentloaded")

            login_user(page)
            time.sleep(5)

            close_menu(page)

            # SLI
            scroll_to_widget(page, HEADINGS["sli"])
            output["sli"] = get_value(page, HEADINGS["sli"])
            # Websockets
            scroll_to_widget(page, HEADINGS["websockets"])
            output["websockets"] = get_value(page, HEADINGS["websockets"], region)
            # duration > 500ms
            scroll_to_widget(page, HEADINGS["duration_over_500ms"])
            output["duration_over_500ms"] = get_table_data(
                page, region, HEADINGS["duration_over_500ms"]
            )
            # duration > 500ms (special cases)
            scroll_to_widget(page, HEADINGS["duration_over_500ms_special"])
            output["duration_over_500ms_special"] = get_table_data(
                page, region, HEADINGS["duration_over_500ms_special"]
            )
            # HTTP 5x
            scroll_to_widget(page, HEADINGS["http_5x"])
            output["http_5x"] = get_table_data(page, region, HEADINGS["http_5x"])
            # Pod restarts
            scroll_to_widget(page, HEADINGS["pod_restarts"])
            output["pod_restarts"] = get_table_data(
                page, region, HEADINGS["pod_restarts"], two_cols=True
            )
            # Pod counts
            scroll_to_widget(page, HEADINGS["pod_counts"])
            output["pod_counts"] = get_table_data(
                page, region, HEADINGS["pod_counts"], three_cols=True
            )
            # Memory utilization
            scroll_to_widget(page, HEADINGS["memory"])
            output["memory"] = get_table_data(
                page, region, HEADINGS["memory"], two_cols=True
            )
            # CPU utilization
            scroll_to_widget(page, HEADINGS["cpu"])
            output["cpu"] = get_table_data(page, region, HEADINGS["cpu"], two_cols=True)

            # Screenshots
            screenshots = take_screenshots(page, region)
            with open(os.path.join(region, "data.json"), "w") as json_file:
                json.dump(output, json_file, indent=4)

            REGION_OUTPUTS[region] = output
            print(f"Data collected for {region}")

        formatted_datetime = (
            date.today().strftime("%Y-%m-%d") + "_" + time.strftime("%H-%M")
        )
        os.makedirs("reports", exist_ok=True)
        generate_pdf("reports", f"service_monitoring_{formatted_datetime}.pdf")

        context.close()
        browser.close()

except Exception as e:
    print("Error occurred: ")
    print(traceback.format_exc())
