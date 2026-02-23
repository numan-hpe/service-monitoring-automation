#Dashboard Type 1 - Data Ingestion to Sustainability Insight Center

class DashboardType1Automation:
    
    def __init__(self, page):
        self.page = page
        self.dashboard_name = "Data Ingestion to Sustainability Insight Center"
        self.result = None
    
    async def get_failed_upload_count(self):
        #Extract the 'Files failed to upload' number from the dashboard.
        try:
            widget = self.page.locator("#widget_box__f2a451e5-523a-43ec-9e89-0ff268d2963e")
            await widget.wait_for(state="visible", timeout=3000)
            value_element = widget.locator('[data-e2e="single-value-widget-value"]')
            count_text = await value_element.inner_text(timeout=5000)
            count = int(count_text.strip())
            print(f"Failed upload count: {count}")
            return count
        except Exception as e:
            print(f"Could not extract failed upload count: {e}")
            return None
    
    async def generate_summary(self):
        #Generate summary based on failed upload count.
        failed_count = await self.get_failed_upload_count()
        if failed_count is None:
            self.result = f"{self.dashboard_name}\nUnable to determine status"
            return
        if failed_count == 0:
            self.result = f"{self.dashboard_name}\nNo errors"
        else:
            self.result = f"{self.dashboard_name}\nFiles failed to upload: {failed_count} "
    
    async def run_checks(self):
        #Run dashboard-specific checks and automation.
        print("Running Dashboard Type 1 checks...")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except:
            await self.page.wait_for_timeout(1000)
        await self.generate_summary()
        print(self.result)
        return self.result
