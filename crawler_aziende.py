import asyncio
from playwright.async_api import async_playwright
import pandas as pd

risultati = []

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = "https://www.paginegialle.it/ricerca/Aziende/Toscana?suggest=true"
        await page.goto(url)
        await page.wait_for_load_state('networkidle')

        # 1) Estraggo tutti gli href delle singole aziende
        elements = await page.query_selector_all("div.search-itm.js-shiny-data-user")
        print(f"Trovati {len(elements)} elementi")

        hrefs = []
        for el in elements:
            div_info = await el.query_selector("div.search-itm__info")
            if div_info:
                link = await div_info.query_selector("a")
                if link:
                    href = await link.get_attribute("href")
                    if href:
                        hrefs.append(href)
                else:
                    print("Link non trovato nel div info")
            else:
                print("Div search-itm__info non trovato")

        # 2) Ciclo su ogni href visitandolo singolarmente
        for href in hrefs:
            await page.goto(href)
            await page.wait_for_load_state('networkidle')

            nome = await page.query_selector('span.scheda-azienda__companyTitle_content')
            if nome:
                nome_text = await nome.inner_text()
                print("Nome:", nome_text)
            else:
                nome_text = "N/A"
                print("Nome non trovato")

            sito = await page.query_selector('a.bttn.bttn--white[title^="sito web"]')
            if sito:
                sito_href = await sito.get_attribute("href")
                print("Sito web:", sito_href)
            else:
                sito_href = "N/A"
                print("Sito web non trovato")

            risultati.append({"nome": nome_text, "sito": sito_href})

        await browser.close()

asyncio.run(main())

# Creo DataFrame e salvo con formattazione
df = pd.DataFrame(risultati)

with pd.ExcelWriter("aziende.xlsx", engine="xlsxwriter") as writer:
    df.to_excel(writer, index=False, sheet_name="Risultati")

    workbook = writer.book
    worksheet = writer.sheets["Risultati"]

    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'center',
        'fg_color': '#DCE6F1',
        'border': 1
    })

    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        max_length = max(
            df[value].astype(str).map(len).max(),
            len(value)
        )
        worksheet.set_column(col_num, col_num, max_length + 5)

    worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
