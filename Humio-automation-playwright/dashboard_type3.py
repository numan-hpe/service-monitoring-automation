#Dashboard Type 3 - Activation Key Onboarding automation.

class DashboardType3Automation:
    
    def __init__(self, page):
        self.page = page
        self.dashboard_name = "Activation Key Onboarding"
        self.result = None

    async def _wait_for_widget_loading(self, widget):
        # Wait for widget loading bar to complete and search to finish.
        try:
            # Wait for loading bar to reach 100%
            max_attempts = 30  # 30 seconds max (30 * 1000ms)
            for attempt in range(max_attempts):
                try:
                    progress_bar = widget.locator('div[style*="width"]')
                    style = await progress_bar.get_attribute('style')
                    if style and 'width' in style:
                        import re
                        width_match = re.search(r'width:\s*(\d+(?:\.\d+)?%)', style)
                        if width_match:
                            width = float(width_match.group(1).rstrip('%'))
                            if width >= 100:
                                print(f"   Loading bar complete (100%)")
                                break
                except:
                    pass
                
                try:
                    search_text = await widget.inner_text(timeout=1000)
                    if "Searching" in search_text or "searching" in search_text:
                        print(f"   Widget still searching, waiting...")
                        await self.page.wait_for_timeout(1000)
                        continue
                except:
                    pass
                if attempt == 0:
                    await self.page.wait_for_timeout(1000)
                elif attempt == max_attempts - 1:
                    print(f"   Widget loading timeout, proceeding anyway")
                    break
                else:
                    await self.page.wait_for_timeout(1000)
                    
        except Exception as e:
            print(f"   Widget load wait error (non-critical): {e}")
            pass

    async def _get_widget_count(self, widget_ids, label, value_selector='[data-e2e="single-value-widget-value"]', wait_for_loading=False):
        try:
            # Handle single ID or list of IDs
            if isinstance(widget_ids, str):
                widget_ids = [widget_ids]
            widget = None
            for widget_id in widget_ids:
                try:
                    temp_widget = self.page.locator(widget_id)
                    await temp_widget.wait_for(timeout=2000)
                    widget = temp_widget
                    break
                except:
                    continue
            
            if not widget:
                # Fallback: try searching by content
                try:
                    all_widgets = self.page.locator('div[id^="widget_box__"]')
                    widget_count = await all_widgets.count()
                    for i in range(widget_count):
                        w = all_widgets.nth(i)
                        try:
                            title_text = await w.locator('.widget-box__header').inner_text(timeout=1000)
                            if label in title_text:
                                widget = w
                                break
                        except:
                            continue
                except:
                    pass
            
            if not widget:
                print(f"Could not extract {label}: Widget not found")
                return 0
            try:
                await widget.scroll_into_view_if_needed(timeout=10000)
            except:
                await self.page.evaluate("window.scrollBy(0, 2000)")
                await self.page.wait_for_timeout(1000)
            await self.page.wait_for_timeout(500)
            if wait_for_loading:
                await self._wait_for_widget_loading(widget)
            try:
                content_div = widget.locator('div.text-deemphasized.w-full.h-full.flex.items-center.justify-center.border-t.border-normal.shadow-base.shadow-inner-md')
                content_text = await content_div.inner_text(timeout=2000)
                if "Search completed. No results found" in content_text:
                    print(f"Found {label} count: 0")
                    return 0
            except:
                pass
            
            try:
                value_element = widget.locator(value_selector)
                count_text = await value_element.inner_text(timeout=3000)
                count = int(count_text.strip())
                print(f"Found {label} count: {count}")
                return count
            except:
                # Fallback to generic data-e2e selector
                try:
                    value_element = widget.locator('div[data-e2e*="value"]')
                    count_text = await value_element.inner_text(timeout=3000)
                    count = int(count_text.strip())
                    print(f"Found {label} count: {count}")
                    return count
                except:
                    print(f"Could not extract {label}: No data found")
                    return 0
        except Exception as e:
            print(f"Could not extract {label}: {e}")
            return 0

    async def _extract_widget_errors(self, widget_ids, label, column_selectors, scroll_horizontal=False, deduplicate=False, wait_timeout=3000):
        try:
            # Handle single ID or list of IDs
            if isinstance(widget_ids, str):
                widget_ids = [widget_ids]
            
            widget = None
            for widget_id in widget_ids:
                try:
                    temp_widget = self.page.locator(widget_id)
                    await temp_widget.wait_for(timeout=2000)
                    widget = temp_widget
                    break
                except:
                    continue
            
            # If hardcoded IDs don't work, try finding by widget title/content
            if not widget:
                print(f"Hardcoded widget IDs not found for {label}, searching by content...")
                try:
                    all_widgets = self.page.locator('div[id^="widget_box__"]')
                    widget_count = await all_widgets.count()
                    for i in range(widget_count):
                        w = all_widgets.nth(i)
                        try:
                            title_text = await w.locator('.widget-box__header').inner_text(timeout=1000)
                            if label in title_text:
                                widget = w
                                print(f"Found widget by content search")
                                break
                        except:
                            continue
                except:
                    pass
            
            if not widget:
                print(f"{label}: Widget not found")
                return None
            
            try:
                await widget.scroll_into_view_if_needed(timeout=10000)
            except:
                await self.page.evaluate("window.scrollBy(0, 2000)")
                await self.page.wait_for_timeout(1000)
            await self.page.wait_for_timeout(wait_timeout)
            
            # Check if widget is still searching and wait if needed
            try:
                searching_div = widget.locator('div.text-deemphasized').filter(has_text="Searching")
                await searching_div.wait_for(timeout=500)
                print(f"   Widget still searching, waiting for completion...")
                await self.page.wait_for_timeout(5000)
            except:
                pass
            
            try:
                table = widget.locator('div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div > table')
                await table.wait_for(timeout=2000)
                
                error_codes = await self._extract_table_with_pagination(
                    widget,
                    column_selectors,
                    scroll_horizontal=scroll_horizontal,
                    deduplicate=deduplicate
                )   
                if error_codes:
                    return error_codes
                else:
                    print(f"   {label}: No error codes found")
                    return None
            
            except:
                try:
                    content_div = widget.locator('div.text-deemphasized.w-full.h-full.flex.items-center.justify-center.border-t.border-normal.shadow-base.shadow-inner-md')
                    content_text = await content_div.inner_text(timeout=2000)
                    if "Search completed. No results found" in content_text or "Searching" in content_text:
                        print(f"{label}: No results found")
                        return None
                    else:
                        print(f"{label}: No results found")
                        return None
                except:
                    print(f"{label}: No results found")
                    return None
        
        except Exception as e:
            print(f"Could not extract {label}: {e}")
            return None

    async def _extract_table_with_pagination(self, widget, column_selectors, scroll_horizontal=False, deduplicate=True):
        all_errors = []
        pagination_found = False
        try:
            # Try multiple pagination selector patterns
            pagination_selectors = [
                "div.flex.flex-initial.justify-between.py-0\\.5.px-6.overflow-auto > humio-resize-observer > ol",
                "div.flex.flex-initial.justify-between > humio-resize-observer > ol",
                "nav ol",
                "div.widget-box__footer button",
            ]        
            pagination_bar = None
            pagination_buttons = None           
            print(f"   Looking for pagination bar in widget...")            
            for selector in pagination_selectors:
                try:
                    test_bar = widget.locator(selector)
                    await test_bar.wait_for(state="visible", timeout=2000)
                    test_buttons = widget.locator(f"{selector} li > button, {selector} button")
                    button_count = await test_buttons.count()
                    if button_count > 0:
                        print(f"   Pagination bar found with {button_count} page buttons")
                        pagination_bar = test_bar
                        pagination_buttons = test_buttons
                        pagination_found = True
                        break
                except:
                    continue
            
            if pagination_found and pagination_buttons:
                button_count = await pagination_buttons.count()
                print(f"   Processing {button_count} pages...")
                for page_idx in range(button_count):
                    try:
                        print(f"   Clicking page {page_idx + 1}/{button_count}...")
                        btn = pagination_buttons.nth(page_idx)
                        # Scroll button into view before clicking
                        try:
                            await btn.scroll_into_view_if_needed(timeout=2000)
                        except:
                            pass
                        for attempt in range(3):  # Click with retry
                            try:
                                await btn.click(timeout=3000)
                                break
                            except:
                                if attempt < 2:
                                    await self.page.wait_for_timeout(500)
                                    continue
                                else:
                                    raise
                        await self.page.wait_for_timeout(2500)  # Wait for content to load
                        if scroll_horizontal:
                            try:
                                await widget.evaluate("""
                                    (element) => {
                                        const scrollableDiv = element.querySelector('div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div');
                                        if (scrollableDiv) {
                                            scrollableDiv.scrollLeft = scrollableDiv.scrollWidth;
                                        }
                                    }
                                """)
                                await self.page.wait_for_timeout(500)
                            except:
                                pass
                        rows = widget.locator('div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div > table > tbody > tr')
                        row_count = await rows.count()
                        print(f"   Page {page_idx + 1}: Found {row_count} rows")
                        page_errors = 0
                        for i in range(row_count):
                            try:
                                column_texts = []
                                for selector in column_selectors:
                                    try:
                                        cell = rows.nth(i).locator(selector)
                                        text = await cell.inner_text(timeout=1500)
                                        if text.strip():
                                            column_texts.append(text.strip())
                                    except:
                                        continue
  
                                if column_texts:
                                    combined = " - ".join(column_texts)
                                    if deduplicate:
                                        if combined not in all_errors:
                                            all_errors.append(combined)
                                            page_errors += 1
                                    else:
                                        all_errors.append(combined)
                                        page_errors += 1
                            except Exception as row_error:
                                continue
                        label = "unique" if deduplicate else "total"
                        print(f"   Page {page_idx + 1}: Extracted {page_errors} {label} errors")
                    except Exception as e:
                        print(f"   Error on page {page_idx + 1}: {e}")
                        continue
                label = "unique" if deduplicate else "total"
                print(f"   Total extracted: {len(all_errors)} {label} errors from {button_count} pages")
                return all_errors if all_errors else None
            else:
                print(f"   No pagination found, extracting from single page...")
        except Exception as e:
            print(f"   Pagination detection error: {e}")
            print(f"   Falling back to single page extraction...")
        try:
            if scroll_horizontal:
                try:
                    await widget.evaluate("""
                        (element) => {
                            const scrollableDiv = element.querySelector('div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div');
                            if (scrollableDiv) {
                                scrollableDiv.scrollLeft = scrollableDiv.scrollWidth;
                            }
                        }
                    """)
                    await self.page.wait_for_timeout(500)
                except:
                    pass
            
            rows = widget.locator('div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div > table > tbody > tr')
            row_count = await rows.count()
            print(f"   Single page: Found {row_count} rows")
            for i in range(row_count):
                try:
                    column_texts = []
                    for selector in column_selectors:
                        try:
                            cell = rows.nth(i).locator(selector)
                            text = await cell.inner_text(timeout=1500)
                            if text.strip():
                                column_texts.append(text.strip())
                        except:
                            continue
                    if column_texts:
                        combined = " - ".join(column_texts)
                        if deduplicate:
                            if combined not in all_errors:
                                all_errors.append(combined)
                        else:
                            all_errors.append(combined)
                except:
                    continue
            label = "unique" if deduplicate else "total"
            print(f"   Single page: Extracted {len(all_errors)} {label} errors")
        except Exception as e:
            print(f"   Error during single page extraction: {e}")
        return all_errors if all_errors else None
   
    async def get_jwt_generation_failed(self):
        """Extract the 'JWT generation failed' count from the dashboard."""
        return await self._get_widget_count(
            "#widget_box__65662d8f-6256-4b4f-975d-30c0a9e7267d",
            "JWT generation failed"
        )
    
    async def get_subscription_key_claim_failure(self):
        """Extract the 'Subscription Key Claim Failure While JWT Generation' count from the dashboard."""
        return await self._get_widget_count(
            "#widget_box__fa904b24-0480-4364-bd19-edf2a7e6a872",
            "Subscription Key Claim Failure while JWT Generation"
        )
    
    async def get_device_not_available_glp_pool(self):
        """Extract the 'Device not available GLP Pool' count from the dashboard."""
        return await self._get_widget_count(
            "#widget_box__a7a91c34-a179-43d1-8017-11ab0b5e62d2",
            "Device not available GLP Pool",
            wait_for_loading=True
        )
    
    async def get_location_tags_sdc_patch_failure(self):
        """Extract the 'Location/Tags/Sdc Patch Failure Count' from the dashboard."""
        return await self._get_widget_count(
            [
                "#widget_box__24c7e9ab-3f07-43b1-985d-96fd8a382fb0",  # env1
                "#widget_box__9ca37872-2576-4389-b9ec-e611738b8b2a",  # env3
                "#widget_box__77afab0c-0551-4d44-97e9-47a171a3df60",  # env2
                "#widget_box__aeba4442-77dc-401c-8deb-16ba500016d5"   # env4
            ],
            "Location/Tags/Sdc Patch Failure",
            wait_for_loading=True
        )
    
    async def get_sdc_patch_failure_errors(self):
        """Extract error details if Location/Tags/Sdc Patch Failure Count > 0."""
        return await self._extract_widget_errors(
            "#widget_box__72e5beef-64dc-4be4-becd-9970e2a6c87f",
            "SDC Patch Failure",
            column_selectors=[]
        )
    
    async def get_oae_errors(self):
        """Extract Error Details During iLO Onboard Activation Job."""
        return await self._extract_widget_errors(
            [
                "#widget_box__fe7e56ad-8d35-45fa-a535-80bb1ce67ab7",  # env1/PRE-PROD
                "#widget_box__77afab0c-0551-4d44-97e9-47a171a3df60",  # env2/ANE1
                "#widget_box__2a97c8f1-8f3b-4b8e-8f9a-8f3b4b8e8f9a",  # env3/EUC1
                "#widget_box__3b97c8f1-8f3b-4b8e-8f9a-8f3b4b8e8f9b"   # env4/USW2
            ],
            "Error Details During iLO Onboard Activation Job",
            column_selectors=['td:nth-child(5) > div', 'td:nth-child(6) > div'],
            deduplicate=False
        )
    
    async def get_error_codes_simple(self):
        """Extract Subscription key claim failure details."""
        return await self._extract_widget_errors(
            "#widget_box__0104eef2-6852-4bbc-ab64-43934aaf268f",
            "Subscription key claim failure details",
            column_selectors=[]
        )
    
    async def get_table_error_codes(self):
        """Extract Subscription key assignment failure details."""
        return await self._extract_widget_errors(
            "#widget_box__79b189d5-cfa5-48be-846f-e9073556b286",
            "Subscription key assignment failure details",
            column_selectors=['td:nth-child(6) > div'],
            deduplicate=False
        )
    
    async def get_pin_generation_failure_details(self):
        """Extract PIN Generation Failure error codes from table."""
        return await self._extract_widget_errors(
            "#widget_box__7edd90fc-15d3-4ba7-9fc0-49b0614780d8",
            "PIN Generation Failure",
            column_selectors=['td:nth-child(7) > div', 'td:nth-child(8) > div'],
            scroll_horizontal=True,
            deduplicate=False
        )
    
    async def get_compute_provision_failure_details(self):
        """Extract Compute Provision Failure error codes."""
        return await self._extract_widget_errors(
            [
                "#widget_box__99bc4e96-1f7b-4d1f-a326-c46ee1ab0623",  # env1/PRE-PROD
                "#widget_box__88bc4e96-1f7b-4d1f-a326-c46ee1ab0624",  # env2/ANE1
                "#widget_box__77bc4e96-1f7b-4d1f-a326-c46ee1ab0625",  # env3/EUC1
                "#widget_box__66bc4e96-1f7b-4d1f-a326-c46ee1ab0626"   # env4/USW2
            ],
            "Compute Provision Failure",
            column_selectors=['td:nth-child(4) > div', 'td:nth-child(5) > div'],
            deduplicate=False
        )
    
    async def generate_summary(self):
        #Generate summary based on all errors.
        try:
            print(f"Scrolling down to reveal all widgets...")
            await self.page.evaluate("""
                () => {
                    window.scrollBy(0, 1000);
                }
            """)
            # Wait for widgets to load after scrolling
            try:
                await self.page.wait_for_load_state("networkidle", timeout=3000)
            except:
                await self.page.wait_for_timeout(500)
        except Exception as e:
            print(f"Could not scroll: {e}")
        self.errors_dict = {}
        errors = []
        
        # Check JWT generation failed
        jwt_count = await self.get_jwt_generation_failed()
        if jwt_count is not None and jwt_count > 0:
            errors.append(f"{jwt_count} JWT generation failed")
            self.errors_dict['jwt'] = jwt_count
        
        # Check Subscription Key Claim Failure
        subscription_count = await self.get_subscription_key_claim_failure()
        if subscription_count is not None and subscription_count > 0:
            errors.append(f"{subscription_count} Subscription Key Claim Failure While JWT Generation")
            self.errors_dict['subscription'] = subscription_count
        
        # Check Device not available GLP Pool
        device_count = await self.get_device_not_available_glp_pool()
        if device_count is not None and device_count > 0:
            errors.append(f"{device_count} Device not available GLP Pool")
            self.errors_dict['device'] = device_count
        
        # Check Location/Tags/Sdc Patch Failure Count
        sdc_count = await self.get_location_tags_sdc_patch_failure()
        if sdc_count is not None and sdc_count > 0:
            errors.append(f"{sdc_count} Location/Tags/Sdc Patch Failure Count")
            self.errors_dict['location'] = sdc_count
            
            # If SDC count > 0, get error details
            sdc_errors = await self.get_sdc_patch_failure_errors()
            if sdc_errors is not None:
                self.errors_dict['sdc_details'] = sdc_errors[:100]
        
        # Check OAE Errors
        oae_errors = await self.get_oae_errors()
        if oae_errors is not None and isinstance(oae_errors, list):
            self.errors_dict['oae'] = oae_errors  # Store as list
        
        # Check Simple Error Codes (skip - no structured data returned)
        simple_errors = await self.get_error_codes_simple()
        
        # Check Table Error Codes
        table_errors = await self.get_table_error_codes()
        if table_errors is not None and isinstance(table_errors, list):
            self.errors_dict['table'] = table_errors
        
        # Check PIN Generation Failure Details
        pin_errors = await self.get_pin_generation_failure_details()
        if pin_errors is not None and isinstance(pin_errors, list):
            self.errors_dict['pin'] = pin_errors  # Store as list
        
        # Check Compute Provision Failure Details
        compute_errors = await self.get_compute_provision_failure_details()
        if compute_errors is not None and isinstance(compute_errors, list):
            self.errors_dict['compute'] = compute_errors  # Store as list
        
        # Generate result
        if errors or self.errors_dict:
            if errors:
                errors_text = " | ".join(errors)
                self.result = f"   ✗ {self.dashboard_name} - {errors_text}"
            else:
                self.result = f"   ✗ {self.dashboard_name} - Has errors"
        else:
            self.result = f"   ✓ {self.dashboard_name} - No errors"
    
    async def run_checks(self):
        #Run dashboard-specific checks and automation.
        print("Running Dashboard Type 3 checks...")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except:
            await self.page.wait_for_timeout(1000)
        await self.generate_summary()
        print(self.result)
        return self.result
