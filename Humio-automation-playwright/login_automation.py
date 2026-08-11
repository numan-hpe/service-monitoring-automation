import asyncio
import os
from playwright.async_api import async_playwright
import logging
from config import USER_EMAIL, BROWSER_USER_DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HumioLoginAutomation:

    def __init__(self, dashboard_url=None, shared_context=None, shared_page=None):
        self.login_url = dashboard_url 
        self.browser_channel = os.getenv("HUMIO_BROWSER_CHANNEL", "msedge").lower()
        self.email = os.getenv("HUMIO_EMAIL", USER_EMAIL)
        self.keep_open = True  # Keep browser open after completion
        
        # Optional: Use shared browser context and page (for unified browser session)
        self.shared_context = shared_context
        self.shared_page = shared_page
        
        self.email_input = 'input[type="email"], input[name="loginfmt"], input[placeholder*="email" i]'
        self.next_button = 'button:has-text("Next"), input[type="submit"][value="Next"]'
        self.yes_button = 'input[type="submit"][value="Yes"], button:has-text("Yes")'
        self.dashboard_element = 'canvas, [class*="dashboard"], [class*="humio"]'
        
        self.browser = None
        self.context = None
        self.page = None

    async def setup_browser(self):
        if self.shared_context:
            logger.info("Using shared browser context")
            self.context = self.shared_context
            self.page = self.shared_page or await self.context.new_page()
            return
        logger.info("Launching browser with persistent profile...")
        self.playwright = await async_playwright().start()
        launch_kwargs = {"headless": False, "no_viewport": True, "args": ["--start-maximized"]}
        if self.browser_channel != "chromium":
            launch_kwargs["channel"] = self.browser_channel
        try:
            os.makedirs(BROWSER_USER_DATA_DIR, exist_ok=True)
            self.context = await self.playwright.chromium.launch_persistent_context(
                BROWSER_USER_DATA_DIR, **launch_kwargs
            )
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            logger.info("Browser launched successfully with persistent profile")
        except Exception as e:
            logger.error(f"Failed to launch browser with channel '{self.browser_channel}': {e}")
            if self.browser_channel != "chromium":
                logger.info("Retrying with default Chromium channel...")
                try:
                    fallback_kwargs = {"headless": False, "no_viewport": True, "args": ["--start-maximized"]}
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        BROWSER_USER_DATA_DIR, **fallback_kwargs
                    )
                    self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                    logger.info("Browser launched successfully with Chromium fallback")
                    return
                except Exception as fallback_error:
                    logger.error(f"Failed to launch Chromium fallback: {fallback_error}")
            raise

    async def navigate_to_login_page(self):
        logger.info(f"Navigating to: {self.login_url}")
        try:
            await self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)
            try:
                await self.page.wait_for_load_state("networkidle", timeout=60000)
            except Exception:
                pass
            logger.info("Page loaded")
        except Exception as e:
            logger.error(f"Failed to navigate: {e}")
            raise

    async def fill_email(self):
        logger.info(f"Waiting for email field...")
        try:
            await self.page.wait_for_selector(self.email_input, timeout=10000)
            logger.info(f"Filling email: {self.email}")
            await self.page.locator(self.email_input).first.fill(self.email)
            logger.info("Email filled")
        except Exception as e:
            logger.error(f"Failed to fill email: {e}")
            raise

    async def click_next(self):
        logger.info("Clicking Next...")
        try:
            await self.page.locator(self.next_button).first.click()
            logger.info("Next clicked - redirecting to mylogin.hpe.com")
        except Exception as e:
            logger.error(f"Failed to click Next: {e}")
            raise

    async def wait_for_auth(self):
        logger.info("Waiting for redirect to mylogin.hpe.com...")
        logger.info("Please complete authentication (fingerprint/password) in the browser")
        try:
            await self.page.wait_for_selector(self.yes_button, timeout=180000)
            logger.info("Authentication completed")
        except Exception as e:
            logger.error(f"Authentication timeout: {e}")
            raise

    async def click_stay_signed_in(self):
        logger.info("Clicking Yes on 'Stay signed in?' page...")
        try:
            try:
                dont_show_checkbox = self.page.locator('input[type="checkbox"]')
                if await dont_show_checkbox.is_visible():
                    await dont_show_checkbox.check()
                    logger.info("Checked 'Don't show this again'")
            except Exception:
                pass
            await self.page.locator(self.yes_button).first.click()
            logger.info("Yes clicked")
        except Exception as e:
            logger.error(f"Failed to click Yes: {e}")
            raise

    async def wait_for_dashboard(self):
        logger.info("Waiting for dashboard to load...")
        try:
            await self.page.wait_for_url("**/dashboards/**", timeout=60000)
            logger.info("Redirected to dashboard")
            await self.page.wait_for_load_state("networkidle", timeout=60000)
            logger.info("Dashboard loaded")
        except Exception as e:
            logger.error(f"Dashboard not loaded: {e}")
            raise

    async def cleanup(self):
        # Close browser and stop Playwright 
        if self.keep_open:
            logger.info("Browser will remain open. Close manually when done.")
            await asyncio.sleep(999999)
        else:
            try:
                if self.page:
                    await self.page.close()
                if self.context and not self.shared_context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
                await asyncio.sleep(0.5)
                if hasattr(self, 'playwright') and self.playwright:
                    await self.playwright.stop()
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

    async def run(self):
        #Main workflow.
        try:
            await self.setup_browser()
            await self.navigate_to_login_page()

            # Check if session is still valid (persistent profile skips login)
            try:
                await self.page.wait_for_url("**/dashboards/**", timeout=10000)
                logger.info("Session still valid, skipping login.")
                return True
            except Exception:
                pass

            # Check if email field appears — if not, SSO session is still valid
            try:
                await self.page.wait_for_selector(self.email_input, timeout=10000)
            except Exception:
                await self.page.wait_for_url("**/dashboards/**", timeout=60000)
                logger.info("SSO session reused, login skipped.")
                return True

            await self.fill_email()
            await self.click_next()
            await self.wait_for_auth()
            await self.click_stay_signed_in()
            await self.wait_for_dashboard()
            # Wait a bit to ensure dashboard is fully loaded
            await self.page.wait_for_timeout(3000)

            logger.info("\n" + "="*50)
            logger.info("LOGIN COMPLETED - DASHBOARD READY")
            logger.info("="*50)
            return True
        except Exception as e:
            logger.error(f"\nFAILED: {e}")
            # Ensure subprocess transports are closed on failure
            try:
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
                if self.playwright:
                    await self.playwright.stop()
            except Exception as cleanup_error:
                logger.error(f"Cleanup error: {cleanup_error}")
            return False

async def main():
    # Default dashboard - can be overridden by passing URL
    automation = HumioLoginAutomation()
    success = await automation.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
