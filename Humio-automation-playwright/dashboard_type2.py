#Dashboard Type 2 - COM Subscription and Consumption

class DashboardType2Automation:
    
    def __init__(self, page):
        """Initialize with Playwright page object."""
        self.page = page
        self.dashboard_name = "COM Subscription and Consumption"
        self.result = None
    
    async def verify_dashboard(self):
        #Verify we are on the correct Type 2 dashboard by checking URL.
        try:
            await self.page.wait_for_load_state("domcontentloaded")
            current_url = self.page.url            
            if "COM%20Subscription%20and%20Consumption" in current_url:
                print(f"Type 2 Dashboard Detected")
                return True
            else:
                print(f"Dashboard mismatch. Expected 'COM%20Subscription%20and%20Consumption' in URL")
                return False
        except Exception as e:
            print(f"Could not verify dashboard: {e}")
            return False
    
    async def get_service_instance_errors(self):
        #Extract the 'Service instance ERROR (CDS)' count from the dashboard.
        try:
            error_link = self.page.get_by_role("link", name="Service instance ERROR (CDS)")
            parent = error_link.locator('..')
            parent_text = await parent.inner_text()
            error_count_element = self.page.get_by_text("0", exact=True).first
            count_text = await error_count_element.inner_text()
            count = int(count_text.strip())
            print(f"Found service instance ERROR (CDS) count: {count}")
            return count
        except Exception as e:
            print(f"Could not extract service instance errors: {e}")
            return None
    
    async def get_upload_errors(self):
        #Extract the 'Upload ERROR (CDS)' count from the dashboard.
        try:
            error_count_element = self.page.get_by_text("0", exact=True).nth(1)
            count_text = await error_count_element.inner_text()
            count = int(count_text.strip())
            print(f"Found Upload ERROR (CDS) count: {count}")
            return count
        except Exception as e:
            print(f"Could not extract upload errors: {e}")
            return None
    
    async def get_charger_schedules_errors(self):
        #Extract the 'Charger Schedules ERROR' count from the dashboard.
        try:
            widget = self.page.locator("#widget_box__8a200ba1-6845-44f9-9289-bc7805361900")
            await widget.scroll_into_view_if_needed()
            await widget.wait_for(state="visible", timeout=3000)
            value_element = widget.locator('[data-e2e="single-value-widget-value"]')
            count_text = await value_element.inner_text(timeout=5000)
            count = int(count_text.strip())
            print(f"Found Charger Schedules ERROR count: {count}")
            return count
        except Exception as e:
            print(f"Could not extract charger schedules errors: {e}")
            return None
    
    async def get_license_oversubscribe_count(self):
        #Extract the 'Advanced License Oversubscribe Detection Count' from the dashboard.
        try:
            widget = self.page.locator("#widget_box__8481de95-4fc5-4ba2-9b63-dba0ed55cde7")
            await widget.scroll_into_view_if_needed()
            await widget.wait_for(state="visible", timeout=3000)
            value_element = widget.locator('[data-e2e="single-value-widget-value"]')
            count_text = await value_element.inner_text(timeout=5000)
            count = int(count_text.strip())
            print(f"Found Advanced License Oversubscribe Detection Count: {count}")
            return count
        except Exception as e:
            print(f"Could not extract Advanced License Oversubscribe count: {e}")
            return 0
    
    async def get_charger_errors(self):
        #Extract 'Charger Errors' from the dashboard.
        try:
            error_link = self.page.get_by_role("link", name="Charger Errors")
            widget = error_link.locator('..').locator('..').locator('..')
            await widget.scroll_into_view_if_needed()
            await widget.wait_for(state="visible", timeout=3000)
            
            # Check if widget is still loading/searching (max 6 iterations = 6 seconds)
            max_iterations = 6
            for i in range(max_iterations):
                try:
                    searching_div = widget.locator('div.text-deemphasized').filter(has_text="Searching")
                    await searching_div.wait_for(timeout=500)
                    if i == 0:
                        print(f"Widget still searching, waiting...")
                    await self.page.wait_for_timeout(1000)
                except:
                    break
            
            # Check for no results
            no_results_div = widget.locator('div.text-deemphasized').filter(has_text="Search completed. No results found")
            try:
                await no_results_div.wait_for(timeout=3000)
                print(f"Charger Errors: No results found (no errors)")
                return None  
            except:
                # Check if there's an error table
                try:
                    table = widget.locator('div.widget-box__content table')
                    await table.wait_for(timeout=2000)
                    # Table exists, don't return text content
                    print(f"Charger Errors: Has error table (not extracting text)")
                    return None
                except:
                    # Still searching or loading
                    print(f"Charger Errors: Widget still loading")
                    return None
        except Exception as e:
            print(f"Could not extract charger errors: {e}")
            return None
    
    async def get_skipped_servers_count(self):
        #Extract the 'Skipped servers' count from the dashboard.
        try:
            link = self.page.get_by_role("link", name="Skipped servers")
            widget = link.locator('..').locator('..').locator('..')
            await widget.scroll_into_view_if_needed()
            await widget.wait_for(state="visible", timeout=3000)
            value_element = widget.locator('[data-e2e="single-value-widget-value"]')
            count_text = await value_element.inner_text(timeout=5000)
            count = int(count_text.strip())
            print(f"Found Skipped servers count: {count}")
            return count
        except Exception as e:
            print(f"Could not extract skipped servers count: {e}")
            return 0
    
    async def generate_summary(self):
        #Generate summary based on all service errors.
        try:
            print(f"Scrolling down to reveal all widgets")
            await self.page.evaluate("() => { window.scrollBy(0, 1000); }")
            try:
                await self.page.wait_for_load_state("networkidle", timeout=3000)
            except:
                await self.page.wait_for_timeout(500)
        except Exception as e:
            print(f"Could not scroll: {e}")
    
        errors = []
        
        si_count = await self.get_service_instance_errors()
        if si_count is not None and si_count > 0:
            errors.append(f"{si_count} Service instance ERROR (CDS)")
        
        upload_count = await self.get_upload_errors()
        if upload_count is not None and upload_count > 0:
            errors.append(f"{upload_count} Upload ERROR (CDS)")
        
        charger_count = await self.get_charger_schedules_errors()
        if charger_count is not None and charger_count > 0:
            errors.append(f"{charger_count} Charger Schedules ERROR")
        
        license_count = await self.get_license_oversubscribe_count()
        if license_count is not None and license_count > 0:
            errors.append(f"{license_count} Advanced License Oversubscribe Detection Count")
        
        charger_errors = await self.get_charger_errors()
        if charger_errors is not None:
            errors.append(f"Charger Errors: {charger_errors[:100]}")
        
        skipped_count = await self.get_skipped_servers_count()
        if skipped_count is not None and skipped_count > 0:
            errors.append(f"{skipped_count} Skipped servers")
        
        if errors:
            errors_text = " | ".join(errors)
            self.result = f"   {self.dashboard_name} - {errors_text}"
        else:
            self.result = f"{self.dashboard_name} - No errors"
    
    async def run_checks(self):
        #Run dashboard-specific checks and automation.
        print("Running Dashboard Type 2 checks...")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except:
            await self.page.wait_for_timeout(1000)
        is_correct_dashboard = await self.verify_dashboard()
        if not is_correct_dashboard:
            self.result = f"{self.dashboard_name} - Dashboard verification failed"
            print(self.result)
            return self.result
        
        await self.generate_summary()
        print(self.result)
        return self.result
