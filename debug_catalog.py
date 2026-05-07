#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

url = "https://book.douban.com/subject/38394251/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, timeout=60000)
    page.wait_for_timeout(2000)

        # Check for dir element
        dir_elem = page.locator('[id*="dir"]')
        print(f"Found {dir_elem.count()} dir elements")

        for i in range(dir_elem.count()):
            elem = dir_elem.nth(i)
            text = elem.inner_text()
            print(f"  Dir {i}: id={elem.get_attribute('id')}, text_len={len(text)}, has_more={'更多' in text or '(更多)' in text}")

    if dir_elem.count() > 0:
        # Get HTML structure
        html = dir_elem.first.inner_html()
        print("Dir HTML snippet:", html[:500] if len(html) > 500 else html)
        print()

        # Check for "更多" link
        more_links = page.get_by_text("更多")
        print(f"Found {more_links.count()} '更多' elements")

        # Try to find clickable elements
        all_links = page.locator('[id*="dir"] a')
        print(f"Found {all_links.count()} links inside dir")

        for i in range(min(all_links.count(), 5)):
            link = all_links.nth(i)
            text = link.inner_text()
            print(f"  Link {i}: {text[:50] if text else '(empty)'}")

        # Execute JavaScript directly
        try:
            page.evaluate('''() => {
                const dir = document.querySelector('[id*="dir"]');
                if (dir) {
                    const shortEl = dir.querySelector('[id*="short"]');
                    const fullEl = dir.querySelector('[id*="full"]');
                    const moreLink = dir.querySelector('a[href*="javascript"]');
                    console.log("short:", shortEl ? "found" : "not found");
                    console.log("full:", fullEl ? "found" : "not found");
                    console.log("moreLink:", moreLink ? "found" : "not found");
                    if (shortEl) shortEl.style.display = 'none';
                    if (fullEl) fullEl.style.display = 'block';
                    if (moreLink) moreLink.click();
                }
            }''')
            page.wait_for_timeout(2000)
            print("Executed JavaScript")

            # Also check for the specific full element
            full_id = page.locator('[id="dir_38394251_full"]')
            print(f"Full element by exact ID: {full_id.count()}")
            if full_id.count() > 0:
                catalog = full_id.first.inner_text()
                print(f"Full catalog length: {len(catalog)}")
                print("Full catalog:", catalog[:500])
        except Exception as e:
            print(f"Error: {e}")

    browser.close()
