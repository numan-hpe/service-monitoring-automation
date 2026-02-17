import time
import io
from PIL import Image
from config import USER_EMAIL, HEADINGS, SCREENSHOT_DATA

logged_in = False

def login_user(page):
    global logged_in
    login_timeout = 180  # Maximum time to wait for login (in seconds)

    page.locator("//a[@href='login/azuread']").wait_for(timeout=30000)
    page.locator("//a[@href='login/azuread']").click()

    if not logged_in:
        try:
            page.locator("//input[@type='email']").wait_for(
                timeout=login_timeout * 1000
            )
            page.locator("//input[@type='email']").fill(USER_EMAIL)

            page.locator("//input[@type='submit']").click()
            time.sleep(3)
            page.locator("//input[@type='submit']").wait_for(
                timeout=login_timeout * 1000
            )
            page.locator("//input[@type='submit']").click()

            page.wait_for_url("**/rugby-daily-check-engine-light**", timeout=login_timeout * 1000)
            logged_in = True
            print("Login successful!")
        except Exception as e:
            print("Login failed: ", e)
            raise e


def wait_for_widgets_to_load(page, max_timeout=180):
    # expand_all_tabs(driver)
    page.wait_for_function(
        "() => document.querySelectorAll('div[aria-label=\"Panel loading bar\"]').length === 0",
        timeout=max_timeout * 1000,
    )


def scroll_to_widget(page, heading=None, xpath=None):
    print(f"Scrolling to widget: '{heading or xpath}'")
    xpath = xpath or f"//*[contains(text(), '{heading}')]"
    attempts = 0
    try:
        scroll_container = page.locator("#page-scrollbar")
        if scroll_container.count() == 0:
            scroll_container = None
    except Exception:
        scroll_container = None

    try:
        while attempts < 20:
            if page.locator(xpath).count() > 0:
                print(f"Found widget: '{heading or xpath}'")
                break
            if scroll_container:
                page.evaluate(
                    "(el) => { el.scrollTop = el.scrollTop + 300; }",
                    scroll_container,
                )
            else:
                page.evaluate("() => window.scrollBy(0, 300)")
            time.sleep(0.5)
            attempts += 1
        widget = page.locator(xpath).first
        widget.scroll_into_view_if_needed()
        if scroll_container:
            page.evaluate(
                "(el) => { el.scrollTop = el.scrollTop - 100; }",
                scroll_container,
            )
        else:
            page.evaluate("() => window.scrollBy(0, -100)")
        time.sleep(0.5)
        wait_for_widgets_to_load(page)
    except Exception as e:
        print(f"\033[91mCould not scroll to widget {heading or xpath}: {e}\033[0m")


def get_value(page, header, region=None):
    xpath = f"//section[contains(@data-testid,'{header}')]//div[@title]"
    if header == HEADINGS["websockets"] and region == "pre-prod":
        xpath = f"(//section[contains(@data-testid,'{header}')]//span)[1]"
    try:
        page.locator(xpath).wait_for(timeout=60000)
        return page.locator(xpath).first.inner_text()
    except Exception as e:
        print(f"\033[91mCould not fetch value for {header}: {e}\033[0m")
        return "--"


def take_screenshots(page, region):
    paths = []

    for name, data in SCREENSHOT_DATA.items():
        xpath = (
            f"//section[contains(@data-testid,'{data['heading']}')]"
            if data["type"] == "small"
            else f"//div[(@data-griditem-key or @data-panelid) and .//span[contains(text(), '{data['heading']}')]]/following-sibling::div[2]"
        )
        scroll_to_widget(page, xpath=xpath)
        img_binary = page.locator(xpath).first.screenshot()
        img = Image.open(io.BytesIO(img_binary))
        filename = f"{region}/{name}"
        paths.append(filename)
        img.save(f"{filename}.png")

    return paths


def get_table_data(page, region, heading, two_cols=False, three_cols=False):
    table_xpath = f"//div[(@data-griditem-key or @data-panelid) and .//span[contains(text(), '{heading}')]]/following-sibling::div[2]//table"
    try:
        name_header = page.locator(f"{table_xpath}//th[@title='name']")
        if name_header.count() > 0:
            name_header.first.click()
            name_header.first.click()
    except Exception:
        pass

    try:
        col_1 = page.locator(f"{table_xpath}//td[1]").all()
        if two_cols or three_cols:
            col_2 = page.locator(f"{table_xpath}//td[2]").all()
        if three_cols:
            col_3 = page.locator(f"{table_xpath}//td[3]").all()
        if len(col_1) == 0:
            return "No data"
        else:
            data = (
                [
                    {
                        "name": el1.inner_text().replace(f"{region}-", ""),
                        "value": el2.inner_text(),
                    }
                    for el1, el2 in zip(col_1, col_2)
                ]
                if two_cols
                else (
                    [
                        {
                            "name": el1.inner_text().replace(f"{region}-", ""),
                            "value": el2.inner_text(),
                            "max": el3.inner_text(),
                        }
                        for el1, el2, el3 in zip(col_1, col_2, col_3)
                    ]
                    if three_cols
                    else [el.inner_text().replace(f"{region}-", "") for el in col_1]
                )
            )
            return data
    except Exception as e:
        print(f"\033[91mCould not fetch table data for {heading}: {e}\033[0m")
        return "--"


def close_menu(page):
    try:
        page.locator("#dock-menu-button").wait_for(timeout=30000)
        page.locator("#dock-menu-button").click()
    except Exception as e:
        print(f"Could not close side menu: {e}")
        pass


def expand_all_tabs(page):
    try:
        tabs = page.locator("//*[@aria-label='Expand row']").all()
        for tab in tabs:
            print("Expanding tab")
            tab.click()
            time.sleep(1)
    except Exception:
        pass
