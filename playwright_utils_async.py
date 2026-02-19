import asyncio
import io
from PIL import Image
import sys
import os

# Import from root config (parent directory)
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import from root config.py
import importlib.util
config_path = os.path.join(root_dir, 'graphana-automation-selenium\config.py')
spec = importlib.util.spec_from_file_location("root_config", config_path)
root_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_config)

USER_EMAIL = root_config.USER_EMAIL
HEADINGS = root_config.GRAPHANA_HEADINGS
SCREENSHOT_DATA = root_config.SCREENSHOT_DATA

logged_in = False

async def login_user_async(page):
    global logged_in
    login_timeout = 180  # Maximum time to wait for login (in seconds)

    await page.locator("//a[@href='login/azuread']").wait_for(timeout=30000)
    await page.locator("//a[@href='login/azuread']").click()

    if not logged_in:
        try:
            await page.locator("//input[@type='email']").wait_for(
                timeout=login_timeout * 1000
            )
            await page.locator("//input[@type='email']").fill(USER_EMAIL)

            await page.locator("//input[@type='submit']").click()
            await asyncio.sleep(3)
            await page.locator("//input[@type='submit']").wait_for(
                timeout=login_timeout * 1000
            )
            await page.locator("//input[@type='submit']").click()

            await page.wait_for_url("**/rugby-daily-check-engine-light**", timeout=login_timeout * 1000)
            logged_in = True
            print("Login successful!")
        except Exception as e:
            print("Login failed: ", e)
            raise e


async def wait_for_widgets_to_load(page, max_timeout=180):
    await page.wait_for_function(
        "() => document.querySelectorAll('div[aria-label=\"Panel loading bar\"]').length === 0",
        timeout=max_timeout * 1000,
    )


async def scroll_to_widget_async(page, heading=None, xpath=None):
    print(f"Scrolling to widget: '{heading or xpath}'")
    xpath = xpath or f"//*[contains(text(), '{heading}')]"
    attempts = 0
    try:
        scroll_container = page.locator("#page-scrollbar")
        if await scroll_container.count() == 0:
            scroll_container = None
    except Exception:
        scroll_container = None

    try:
        while attempts < 20:
            if await page.locator(xpath).count() > 0:
                print(f"Found widget: '{heading or xpath}'")
                break
            if scroll_container:
                await page.evaluate(
                    "(el) => { el.scrollTop = el.scrollTop + 300; }",
                    await scroll_container.element_handle(),
                )
            else:
                await page.evaluate("() => window.scrollBy(0, 300)")
            await asyncio.sleep(0.5)
            attempts += 1
        widget = page.locator(xpath).first
        await widget.scroll_into_view_if_needed()
        if scroll_container:
            await page.evaluate(
                "(el) => { el.scrollTop = el.scrollTop - 100; }",
                await scroll_container.element_handle(),
            )
        else:
            await page.evaluate("() => window.scrollBy(0, -100)")
        await asyncio.sleep(0.5)
        await wait_for_widgets_to_load(page)
    except Exception as e:
        print(f"\033[91mCould not scroll to widget {heading or xpath}: {e}\033[0m")


async def get_value_async(page, header, region=None):
    xpath = f"//section[contains(@data-testid,'{header}')]//div[@title]"
    if header == HEADINGS["websockets"] and region == "pre-prod":
        xpath = f"(//section[contains(@data-testid,'{header}')]//span)[1]"
    try:
        await page.locator(xpath).wait_for(timeout=60000)
        return await page.locator(xpath).first.inner_text()
    except Exception as e:
        print(f"\033[91mCould not fetch value for {header}: {e}\033[0m")
        return "--"


async def take_screenshots_async(page, region):
    paths = []

    for name, data in SCREENSHOT_DATA.items():
        xpath = (
            f"//section[contains(@data-testid,'{data['heading']}')]"
            if data["type"] == "small"
            else f"//div[(@data-griditem-key or @data-panelid) and .//span[contains(text(), '{data['heading']}')]]/following-sibling::div[2]"
        )
        await scroll_to_widget_async(page, xpath=xpath)
        img_binary = await page.locator(xpath).first.screenshot()
        img = Image.open(io.BytesIO(img_binary))
        filename = f"{region}/{name}"
        paths.append(filename)
        img.save(f"{filename}.png")

    return paths


async def get_table_data_async(page, region, heading, two_cols=False, three_cols=False):
    table_xpath = f"//div[(@data-griditem-key or @data-panelid) and .//span[contains(text(), '{heading}')]]/following-sibling::div[2]//table"
    try:
        name_header = page.locator(f"{table_xpath}//th[@title='name']")
        if await name_header.count() > 0:
            await name_header.first.click()
            await name_header.first.click()
    except Exception:
        pass

    try:
        col_1 = await page.locator(f"{table_xpath}//td[1]").all()
        if two_cols or three_cols:
            col_2 = await page.locator(f"{table_xpath}//td[2]").all()
        if three_cols:
            col_3 = await page.locator(f"{table_xpath}//td[3]").all()
        if len(col_1) == 0:
            return "No data"
        else:
            if two_cols:
                data = []
                for el1, el2 in zip(col_1, col_2):
                    text1 = await el1.inner_text()
                    text2 = await el2.inner_text()
                    data.append({
                        "name": text1.replace(f"{region}-", ""),
                        "value": text2,
                    })
            elif three_cols:
                data = []
                for el1, el2, el3 in zip(col_1, col_2, col_3):
                    text1 = await el1.inner_text()
                    text2 = await el2.inner_text()
                    text3 = await el3.inner_text()
                    data.append({
                        "name": text1.replace(f"{region}-", ""),
                        "value": text2,
                        "max": text3,
                    })
            else:
                data = []
                for el in col_1:
                    text = await el.inner_text()
                    data.append(text.replace(f"{region}-", ""))
            return data
    except Exception as e:
        print(f"\033[91mCould not fetch table data for {heading}: {e}\033[0m")
        return "--"


async def close_menu_async(page):
    try:
        await page.locator("#dock-menu-button").wait_for(timeout=30000)
        await page.locator("#dock-menu-button").click()
    except Exception as e:
        print(f"Could not close side menu: {e}")
        pass

