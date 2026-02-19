import asyncio
import os
from playwright.async_api import async_playwright
import logging
import json
from config import USER_EMAIL, SESSION_COOKIES_PATH

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
        # If shared context is provided, use it directly
        if self.shared_context:
            logger.info("Using shared browser context")
            self.context = self.shared_context
            self.page = self.shared_page or await self.context.new_page()
            return
        
        logger.info("Launching browser...")
        self.playwright = await async_playwright().start()

        launch_kwargs = {"headless": False, "args": ["--start-maximized"]}
        if self.browser_channel != "chromium":
            launch_kwargs["channel"] = self.browser_channel

        try:
            self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            self.context = await self.browser.new_context(no_viewport=True)
            await self._load_session_cookies()
            self.page = await self.context.new_page()
            logger.info("Browser launched successfully")
        except Exception as e:
            logger.error(f"Failed to launch browser with channel '{self.browser_channel}': {e}")
            if self.browser_channel != "chromium":
                logger.info("Retrying with default Chromium channel...")
                try:
                    fallback_kwargs = {"headless": False, "args": ["--start-maximized"]}
                    self.browser = await self.playwright.chromium.launch(**fallback_kwargs)
                    self.context = await self.browser.new_context(no_viewport=True)
                    await self._load_session_cookies()
                    self.page = await self.context.new_page()
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

    async def _load_session_cookies(self):
        """Load cookies exported from Selenium to reuse existing login session."""
        try:
            if not os.path.exists(SESSION_COOKIES_PATH):
                return
            with open(SESSION_COOKIES_PATH, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            if not cookies:
                return
            # Playwright expects keys: name, value, domain, path, expires, httpOnly, secure, sameSite
            normalized = []
            for c in cookies:
                cookie = {
                    "name": c.get("name"),
                    "value": c.get("value"),
                    "domain": c.get("domain"),
                    "path": c.get("path", "/"),
                    "expires": c.get("expiry", -1),
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "sameSite": "Lax",
                }
                if cookie["name"] and cookie["value"] and cookie["domain"]:
                    normalized.append(cookie)
            if normalized:
                await self.context.add_cookies(normalized)
                logger.info("Loaded session cookies from Selenium export")
        except Exception as e:
            logger.warning(f"Could not load session cookies: {e}")

    async def fill_email(self):
        logger.info(f"Waiting for email field...")
        try:
            # Wait for email field to be visible
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
            # Wait for Stay signed in page to appear
            await self.page.wait_for_selector(self.yes_button, timeout=180000)
            logger.info("Authentication completed")
        except Exception as e:
            logger.error(f"Authentication timeout: {e}")
            raise

    async def click_stay_signed_in(self):
        """Click Yes on 'Stay signed in?' page."""
        logger.info("Clicking Yes on 'Stay signed in?' page...")
        try:
            # Check 'Don't show this again' checkbox if present
            try:
                dont_show_checkbox = self.page.locator('input[type="checkbox"]')
                if await dont_show_checkbox.is_visible():
                    await dont_show_checkbox.check()
                    logger.info("Checked 'Don't show this again'")
            except Exception:
                pass
            
            # Click Yes button
            await self.page.locator(self.yes_button).first.click()
            logger.info("Yes clicked")
        except Exception as e:
            logger.error(f"Failed to click Yes: {e}")
            raise

    async def wait_for_dashboard(self):
        """Wait for dashboard to load."""
        logger.info("Waiting for dashboard to load...")
        try:
            # Wait for URL to change to dashboard
            await self.page.wait_for_url("**/dashboards/**", timeout=60000)
            logger.info("Redirected to dashboard")
            # Wait for dashboard content to load
            await self.page.wait_for_load_state("networkidle", timeout=60000)
            logger.info("Dashboard loaded")
        except Exception as e:
            logger.error(f"Dashboard not loaded: {e}")
            raise

    async def cleanup(self):
        """Close browser properly to avoid subprocess warnings."""
        if self.keep_open:
            logger.info("Browser will remain open. Close manually when done.")
            # Keep script running
            await asyncio.sleep(999999)
        else:
            try:
                # Close in reverse order: page -> context -> browser -> playwright
                if self.page:
                    await self.page.close()
                if self.context and not self.shared_context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
                # Give time for subprocess cleanup
                await asyncio.sleep(0.5)
                if hasattr(self, 'playwright') and self.playwright:
                    await self.playwright.stop()
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

    async def run(self):
        """Main workflow."""
        try:
            await self.setup_browser()
            await self.navigate_to_login_page()
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
        # No finally block - let caller manage cleanup


async def main():
    """Entry point."""
    # Default dashboard - can be overridden by passing URL
    automation = HumioLoginAutomation()
    success = await automation.run()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
