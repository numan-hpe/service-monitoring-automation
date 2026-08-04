#Dashboard Type 3 - Activation Key Onboarding automation.

class DashboardType3Automation:
    
    def __init__(self, page):
        """Initialize with Playwright page object."""
        self.page = page
        self.dashboard_name = "Activation Key Onboarding"
        self.result = None

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
                    
                    # Try to find page buttons
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
                        # Click with retry
                        for attempt in range(3):
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
                    
                        # Scroll horizontally if needed
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
                        
                        # Extract from current page with fallback selectors
                        row_selectors = [
                            'div.widget-box__content.z-20 > div > div.flex.flex-1.flex-col.h-full.table-widget > div.flex.flex-col.flex-1.overflow-auto.h-full > table > tbody > tr',
                            'div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div > table > tbody > tr',
                            'div.widget-box__content table tbody tr',
                            'table tbody tr',
                            'tbody tr',
                            'tr[role="row"]',
                        ]
                        rows = None
                        for row_selector in row_selectors:
                            try:
                                test_rows = widget.locator(row_selector)
                                count = await test_rows.count()
                                if count > 0:
                                    rows = test_rows
                                    break
                            except:
                                continue
                        
                        if rows is None:
                            print(f"   Page {page_idx + 1}: No table rows found with any selector")
                            continue
                            
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
                # No pagination found, extract from single page
                print(f"   No pagination found, extracting from single page...")
        except Exception as e:
            print(f"   Pagination detection error: {e}")
            print(f"   Falling back to single page extraction...")
        
        # Single page extraction (fallback)
        try:
            if scroll_horizontal:
                try:
                    await widget.evaluate("""
                        (element) => {
                            const scrollableDiv = element.querySelector('div.widget-box__content.z-20 > div > div.flex.flex-1.flex-col.h-full.table-widget > div')
                                || element.querySelector('div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div');
                            if (scrollableDiv) {
                                scrollableDiv.scrollLeft = scrollableDiv.scrollWidth;
                            }
                        }
                    """)
                    await self.page.wait_for_timeout(500)
                except:
                    pass
            
            # Try multiple row selectors
            row_selectors = [
                'div.widget-box__content.z-20 > div > div.flex.flex-1.flex-col.h-full.table-widget > div.flex.flex-col.flex-1.overflow-auto.h-full > table > tbody > tr',
                'div.widget-box__content.z-40 > div > div.flex.flex-1.flex-col.h-full.table-widget > div > table > tbody > tr',
                'div.widget-box__content table tbody tr',
                'table tbody tr',
                'tbody tr',
                'tr[role="row"]',
            ]
            rows = None
            for row_selector in row_selectors:
                try:
                    test_rows = widget.locator(row_selector)
                    count = await test_rows.count()
                    if count > 0:
                        rows = test_rows
                        break
                except:
                    continue
            
            if rows is None:
                print(f"   Single page: No table rows found with any selector")
                return all_errors if all_errors else None
                
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
        #Extract the 'JWT generation failed' count from the dashboard.
        try:
            widget = self.page.locator("#widget_box__65662d8f-6256-4b4f-975d-30c0a9e7267d")
            await widget.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(500)
            value_element = widget.locator('[data-e2e="single-value-widget-value"]')
            count_text = await value_element.inner_text(timeout=5000)
            count = int(count_text.strip())
            print(f"Found JWT generation failed count: {count}")
            return count
            
        except Exception as e:
            print(f"Could not extract JWT generation failed count: {e}")
            return 0
    
    async def get_subscription_key_claim_failure(self):
        #Extract the 'Subscription Key Claim Failure While JWT Generation' count from the dashboard.
        try:
            widget = self.page.locator("#widget_box__fa904b24-0480-4364-bd19-edf2a7e6a872")
            await widget.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(500)
            value_element = widget.locator('[data-e2e="single-value-widget-value"]')
            count_text = await value_element.inner_text(timeout=5000)
            count = int(count_text.strip())
            print(f"Found Subscription Key Claim Failure while JWT Generation count: {count}")
            return count
            
        except Exception as e:
            print(f"Could not extract Subscription Key Claim Failure while JWT Generation count: {e}")
            return 0
    
    async def get_device_not_available_glp_pool(self):
        #Extract the 'Device not available GLP Pool' count from the dashboard.
        try:
            widget = self.page.locator("#widget_box__a7a91c34-a179-43d1-8017-11ab0b5e62d2")
            await widget.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(500)
            value_element = widget.locator('[data-e2e="single-value-widget-value"]')
            count_text = await value_element.inner_text(timeout=5000)
            count = int(count_text.strip())
            print(f"Found Device not available GLP Pool count: {count}")
            return count
            
        except Exception as e:
            print(f"Could not extract Device not available GLP Pool count: {e}")
            return 0
    
    async def get_location_tags_sdc_patch_failure(self):
        #Extract the 'Location/Tags/Sdc Patch Failure Count' from the dashboard.
        WIDGET_ID = "#widget_box__24c7e9ab-3f07-43b1-985d-96fd8a382fb0"
        VALUE_SEL = "div.widget-box__content.z-20 > div > div.w-full.h-full > div > div > div"
        try:
            widget = self.page.locator(WIDGET_ID)
            try:
                await widget.wait_for(state="visible", timeout=5000)
            except:
                print(f"Location/Tags/Sdc Patch Failure widget not found")
                return 0
            try:
                await widget.scroll_into_view_if_needed(timeout=5000)
            except:
                await self.page.evaluate("window.scrollBy(0, 2000)")
            await self.page.wait_for_timeout(500)

            # Try the exact value selector first
            try:
                value_element = widget.locator(VALUE_SEL)
                count_text = await value_element.inner_text(timeout=3000)
                count = int(count_text.strip())
                print(f"Found Location/Tags/Sdc Patch Failure Count: {count}")
                return count
            except:
                pass

            # Fallback selectors
            for sel in ['[data-e2e="single-value-widget-value"]', 'div[data-e2e*="value"]']:
                try:
                    count_text = await widget.locator(sel).inner_text(timeout=2000)
                    count = int(count_text.strip())
                    print(f"Found Location/Tags/Sdc Patch Failure Count: {count}")
                    return count
                except:
                    continue

            print(f"Location/Tags/Sdc Patch Failure: No data found (0)")
            return 0
        except Exception as e:
            print(f"Could not extract Location/Tags/Sdc Patch Failure Count: {e}")
            return 0
    
    async def get_sdc_patch_failure_errors(self):
        #Extract error details if Location/Tags/Sdc Patch Failure Count > 0.
        try:
            widget = self.page.locator("#widget_box__9ca37872-2576-4389-b9ec-e611738b8b2a")
            await widget.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(3000)
            
            # Check if there's a "No results" message
            try:
                content_div = widget.locator('div.text-deemphasized.w-full.h-full.flex.items-center.justify-center.border-t.border-normal.shadow-base.shadow-inner-md')
                content_text = await content_div.inner_text(timeout=2000)
                if "Search completed. No results found" in content_text:
                    print(f"Location/Tags/Sdc Patch Failure: No results found")
                    return None
            except:
                pass
            
            # Check number of pages before extracting
            try:
                pagination_ol = widget.locator("div.flex.flex-initial.justify-between.py-0\\.5.px-6.overflow-auto > humio-resize-observer > ol")
                await pagination_ol.wait_for(state="visible", timeout=2000)
                
                # Count page buttons
                page_buttons = widget.locator("div.flex.flex-initial.justify-between.py-0\\.5.px-6.overflow-auto > humio-resize-observer > ol > li > button")
                num_pages = await page_buttons.count()
                
                print(f"   Found {num_pages} pages in Location/Tags/Sdc Patch Failure table")
                
                # If more than 10 pages, get total count and return summary instead
                if num_pages > 10:
                    try:
                        # Get total count from the count widget
                        count_widget = self.page.locator("#widget_box__54fb95ac-34ec-4575-bcf9-9ec0f27f06b5")
                        count_element = count_widget.locator("div.widget-box__content.z-40 > div > div.w-full.h-full > div > div > div")
                        total_count = await count_element.inner_text(timeout=3000)
                        total_count = int(total_count.strip())
                        print(f"   Too many pages ({num_pages}), using summary. Total errors: {total_count}")
                        return [f"Multiple occurrences ({total_count} total errors across {num_pages} pages)"]
                    except:
                        print(f"   Too many pages ({num_pages}), using summary")
                        return [f"Multiple occurrences (across {num_pages} pages)"]
            except:
                print(f"   No pagination found or single page")
            
            # Use pagination helper to extract from all pages (column 5)
            error_codes = await self._extract_table_with_pagination(
                widget,
                ['td:nth-child(5) > div'],
                scroll_horizontal=False,
                deduplicate=True
            )
            
            if error_codes:
                preview = ", ".join(error_codes[:5])
                print(f"Found Location/Tags/Sdc Patch Failure Details: {preview}...")
                return error_codes
            else:
                print(f"   Location/Tags/Sdc Patch Failure: No error details found")
                return None
                
        except Exception as e:
            print(f"Could not extract Location/Tags/Sdc Patch Failure Details: {e}")
            return None
    
    async def get_oae_errors(self):
        #Extract Error Details During iLO Onboard Activation Job.
        WIDGET_ID = "#widget_box__fe7e56ad-8d35-45fa-a535-80bb1ce67ab7"
        TABLE_ROWS = "div.widget-box__content.z-20 > div > div.flex.flex-1.flex-col.h-full.table-widget > div.flex.flex-col.flex-1.overflow-auto.h-full > table > tbody > tr"
        NO_RESULTS_SEL = "div.widget-box__content.z-20 > div > div.text-deemphasized.w-full.h-full.flex.items-center.justify-center.border-t.border-normal.shadow-base.shadow-inner-md"
        try:
            widget = self.page.locator(WIDGET_ID)
            try:
                await widget.wait_for(state="visible", timeout=5000)
            except:
                print(f"Error Details During iLO Onboard Activation Job widget not found")
                return None

            try:
                await widget.scroll_into_view_if_needed(timeout=5000)
            except:
                await self.page.evaluate("window.scrollBy(0, 2000)")
            await self.page.wait_for_timeout(1000)

            # Wait for search to complete (up to 15 seconds)
            for _ in range(15):
                try:
                    searching_div = widget.locator('div.text-deemphasized').filter(has_text="Searching")
                    await searching_div.wait_for(state="visible", timeout=500)
                    await self.page.wait_for_timeout(1000)
                except:
                    break

            # Check for no results
            try:
                no_results = widget.locator(NO_RESULTS_SEL)
                text = await no_results.inner_text(timeout=1500)
                if "No results found" in text:
                    print(f"Error Details During iLO Onboard Activation Job: No results found")
                    return None
            except:
                pass

            # Extract table with pagination
            error_codes = await self._extract_table_with_pagination(
                widget,
                ['td:nth-child(5) > div', 'td:nth-child(6) > div'],
                scroll_horizontal=False,
                deduplicate=False
            )
            if error_codes:
                preview = ", ".join(error_codes[:5])
                print(f"   Found Error Details During iLO Onboard Activation Job: {preview}")
                return error_codes
            else:
                print(f"Error Details During iLO Onboard Activation Job: No results found")
                return None
        except Exception as e:
            print(f"Could not extract Error Details During iLO Onboard Activation Job: {e}")
            return None
    
    async def get_error_codes_simple(self):
        #Extract Subscription key claim failure details.
        try:
            widget = self.page.locator("#widget_box__0104eef2-6852-4bbc-ab64-43934aaf268f")
            await widget.scroll_into_view_if_needed(timeout=5000)
            await self.page.wait_for_timeout(500)
            try:
                content_div = widget.locator('div.text-deemphasized.w-full.h-full.flex.items-center.justify-center.border-t.border-normal.shadow-base.shadow-inner-md')
                content_text = await content_div.inner_text(timeout=2000)
                
                if "Search completed. No results found" in content_text or "Searching" in content_text:
                    print(f"Subscription key claim failure details: No results found")
                    return None
                else:
                    print(f"Found Subscription key claim failure details")
                    return None  # Don't return text, only structured data
            except:
                print(f"Subscription key claim failure details: No results found")
                return None
                
        except Exception as e:
            print(f"Subscription key claim failure details: No results found")
            return None
    
    async def get_table_error_codes(self):
        #Extract Subscription key assignment failure details.
        try:
            widget = self.page.locator("#widget_box__79b189d5-cfa5-48be-846f-e9073556b286")
            await widget.scroll_into_view_if_needed()
            # Wait longer for widget to fully load
            await self.page.wait_for_timeout(3000)
            
            # Check if widget is still searching and wait if needed
            try:
                searching_div = widget.locator('div.text-deemphasized').filter(has_text="Searching")
                await searching_div.wait_for(timeout=500)
                print(f"Widget still searching, waiting for completion...")
                await self.page.wait_for_timeout(5000)
            except:
                pass
            
            try:
                no_results = widget.locator('div.text-deemphasized').filter(has_text="Search completed. No results found")
                await no_results.wait_for(timeout=2000)
                print(f"   Subscription key assignment failure details: No results found")
                return None
            except:
                pass
            
            # Use pagination helper to extract from all pages
            error_codes = await self._extract_table_with_pagination(
                widget,
                ['td:nth-child(6) > div'],
                scroll_horizontal=False,
                deduplicate=False
            )
            
            if error_codes:
                preview = ", ".join(error_codes[:5])
                print(f"Found Subscription key assignment failure details: {preview}...")
                return error_codes
            else:
                print(f"   Subscription key assignment failure details: No data found")
                return None
                
        except Exception as e:
            print(f"   Could not extract Subscription key assignment failure details: {e}")
            return None
    
    async def get_pin_generation_failure_details(self):
        #Extract PIN Generation Failure error codes from table.
        WIDGET_ID = "#widget_box__7edd90fc-15d3-4ba7-9fc0-49b0614780d8"
        NO_RESULTS_SEL = "div.widget-box__content.z-20 > div > div.text-deemphasized.w-full.h-full.flex.items-center.justify-center.border-t.border-normal.shadow-base.shadow-inner-md"
        try:
            widget = self.page.locator(WIDGET_ID)
            try:
                await widget.wait_for(state="visible", timeout=5000)
            except:
                print(f"PIN Generation Failure widget not found")
                return None

            try:
                await widget.scroll_into_view_if_needed(timeout=5000)
            except:
                await self.page.evaluate("window.scrollBy(0, 2000)")
            await self.page.wait_for_timeout(1000)

            # Wait for search to complete (up to 15 seconds)
            for _ in range(15):
                try:
                    searching_div = widget.locator('div.text-deemphasized').filter(has_text="Searching")
                    await searching_div.wait_for(state="visible", timeout=500)
                    await self.page.wait_for_timeout(1000)
                except:
                    break

            # Check for no results
            try:
                no_results = widget.locator(NO_RESULTS_SEL)
                text = await no_results.inner_text(timeout=1500)
                if "No results found" in text:
                    print(f"PIN Generation Failure: No results found")
                    return None
            except:
                pass

            # Extract table with pagination
            error_codes = await self._extract_table_with_pagination(
                widget,
                ['td:nth-child(7) > div', 'td:nth-child(8) > div'],
                scroll_horizontal=True,
                deduplicate=False
            )
            if error_codes:
                preview = ", ".join(error_codes[:3])
                print(f"   Found PIN Generation Failure errors: {preview}...")
                return error_codes
            else:
                print(f"PIN Generation Failure: No results found")
                return None
        except Exception as e:
            print(f"Could not extract PIN Generation Failure details: {e}")
            return None
    
    async def get_compute_provision_failure_details(self):
        #Extract Compute Provision Failure error codes.
        WIDGET_ID = "#widget_box__99bc4e96-1f7b-4d1f-a326-c46ee1ab0623"
        NO_RESULTS_SEL = "div.widget-box__content.z-20 > div > div.text-deemphasized.w-full.h-full.flex.items-center.justify-center.border-t.border-normal.shadow-base.shadow-inner-md"
        try:
            widget = self.page.locator(WIDGET_ID)
            try:
                await widget.wait_for(state="visible", timeout=5000)
            except:
                print(f"Compute Provision Failure Details widget not found")
                return None

            try:
                await widget.scroll_into_view_if_needed(timeout=5000)
            except:
                await self.page.evaluate("window.scrollBy(0, 2000)")
            await self.page.wait_for_timeout(1000)

            # Wait for search to complete (up to 15 seconds)
            for _ in range(15):
                try:
                    searching_div = widget.locator('div.text-deemphasized').filter(has_text="Searching")
                    await searching_div.wait_for(state="visible", timeout=500)
                    await self.page.wait_for_timeout(1000)
                except:
                    break

            # Check for no results
            try:
                no_results = widget.locator(NO_RESULTS_SEL)
                text = await no_results.inner_text(timeout=1500)
                if "No results found" in text:
                    print(f"Compute Provision Failure Details: No results found")
                    return None
            except:
                pass

            # Extract table with pagination
            error_codes = await self._extract_table_with_pagination(
                widget,
                ['td:nth-child(4) > div', 'td:nth-child(5) > div'],
                scroll_horizontal=False,
                deduplicate=False
            )
            if error_codes:
                print(f"   Found Compute Provision Failure errors: {len(error_codes)} errors")
                return error_codes
            else:
                print(f"Compute Provision Failure Details: No results found")
                return None
        except Exception as e:
            print(f"Could not extract Compute Provision Failure Details: {e}")
            return None
    
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
