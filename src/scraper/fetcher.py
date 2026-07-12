import asyncio
from playwright.async_api import async_playwright


async def fetch_html(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            viewport={"width": 600, "height": 962},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            is_mobile=True,
            has_touch=True,
        )

        # Внедряем твои реальные куки
        await context.add_cookies(
            [
                {
                    "name": "sessid",
                    "value": "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9."
                    "eyJleHAiOjE3ODM4OTA5MjQsImlhdCI6MTc4MzgwNDUy"
                    "NCwidSI6MjI0NDgzMjQ2LCJwIjoxMDU5MTk2ODksInMiOi"
                    "JkODdiNTM3YmExNjhhYjQzMWNmZTAyNzU2ZGEyOGY2ZC4xNzgz"
                    "ODA0NTI0IiwiaCI6ImNjN2RkM2VmZGUzMTYyZjg1NGM5YWFiNjVl"
                    "NjkwNWU5XzE3ODM4MDQ1MjQiLCJkIjoiM2JtbjJrd3kuMW10M3Jz"
                    "LnJzeHJtMjBmczJnMCIsInBsIjoiZGVza3RvcCIsImV4dHJhIjpu"
                    "dWxsfQ.el-pvSwX0JbIeW6paWIgJArldTdNIml9l3nfNZYEW4GmWU"
                    "r2M6tUPDGJLlsWRUMAl12MJECs0bXMO7UoaDQBiQ",
                    "domain": ".avito.ru",
                    "path": "/",
                },
                {
                    "name": "u",
                    "value": "3bmn2kwy.1mt3rs.rsxrm20fs2g0",
                    "domain": ".avito.ru",
                    "path": "/",
                },
                {
                    "name": "uxs_uid",
                    "value": "053a6ad0-31a7-11f1-a722-1f26620f5ed0",
                    "domain": ".avito.ru",
                    "path": "/",
                },
                {
                    "name": "v",
                    "value": "1783804524",
                    "domain": ".avito.ru",
                    "path": "/",
                },
            ]
        )

        page = await context.new_page()

        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = {
                runtime: {},
            };
        """
        )

        await page.goto(url, wait_until="domcontentloaded")

        await asyncio.sleep(2)

        html_content = await page.content()
        await browser.close()

        return html_content
