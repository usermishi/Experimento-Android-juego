import asyncio
from playwright.async_api import async_playwright, expect
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to the local HTML file
        file_path = os.path.abspath('index.html')
        await page.goto(f'file://{file_path}')

        # Wait for the loading screen to disappear
        await expect(page.locator("#loading-screen")).not_to_be_visible(timeout=15000) # Increased timeout just in case
        await expect(page.locator("#character-selection-screen")).to_be_visible()


        # --- 1. Character and Weapon Selection ---
        await page.get_by_text("Seraphina").click()
        await page.get_by_text("Bastón de Mago").click()
        await page.get_by_role("button", name="Comenzar Juego").click()
        await expect(page.locator("#game-container")).to_be_visible()
        await page.wait_for_timeout(500)

        # --- 2. Use Skill ---
        # Take some initial damage by moving into a monster
        await page.keyboard.press('ArrowRight', delay=500)
        await page.keyboard.press('ArrowDown', delay=500)
        await page.wait_for_timeout(1500) # Wait for combat to occur

        # Use healing skill
        await page.locator("#ability-btn").click()
        await expect(page.locator("#ability-btn")).to_be_disabled()
        await page.wait_for_timeout(500)

        # --- 3. Build a Shrine ---
        await page.locator("#build-btn").click()
        await expect(page.locator("#build-modal")).to_be_visible()
        # Click the build button for the shrine
        await page.locator('button[data-building="shrine"]').click()
        await expect(page.locator("#build-modal")).not_to_be_visible() # Modal should close
        # Place the shrine on the canvas
        await page.locator("#game-canvas").click(position={"x": 300, "y": 300})
        await page.wait_for_timeout(500)

        # --- 4. Use the Shop ---
        await page.locator("#shop-btn").click()
        await expect(page.locator("#shop-modal")).to_be_visible()
        # Upgrade weapon
        await page.locator("#upgrade-weapon-btn").click()
        await page.locator(".modal .close-btn").first.click() # Close shop
        await page.wait_for_timeout(500)

        # --- 5. Final Screenshot ---
        # Move the player a bit to show everything
        await page.keyboard.press('ArrowLeft', delay=1000)

        screenshot_path = 'jules-scratch/verification/final_verification.png'
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())