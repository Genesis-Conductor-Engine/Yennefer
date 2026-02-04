from playwright.sync_api import sync_playwright
import time

def verify_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # 1. Verify Observatory (Root)
            print("Navigating to Observatory...")
            page.goto("http://localhost:5173/", timeout=30000)
            page.wait_for_selector(".observatory", timeout=10000)
            # Wait for three.js canvas
            time.sleep(3)
            page.screenshot(path="verification_observatory.png")
            print("Observatory screenshot saved.")

            # 2. Verify Cosmos
            print("Navigating to Cosmos...")
            page.goto("http://localhost:5173/cosmos", timeout=30000)
            # p5 creates a canvas inside the div, but react-p5 might wrap it.
            # Let's wait for any canvas.
            page.wait_for_selector("canvas", timeout=10000)
            time.sleep(3)
            page.screenshot(path="verification_cosmos.png")
            print("Cosmos screenshot saved.")

        except Exception as e:
            print(f"Error: {e}")
            # print page source to debug
            # print(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    verify_all()
