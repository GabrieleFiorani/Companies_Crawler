import asyncio
from playwright.async_api import async_playwright
import pandas as pd


from crawler_siti import *


risultati = []

NUM_PAGINE = int(input("Quante pagine vuoi visitare?: "))
REGIONE = input("Digita la regione per la ricerca (es. Lombardia, Lazio, etc.): ")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for pagina in range(1, NUM_PAGINE + 1):
            url = f"https://www.paginegialle.it/ricerca/aziende/{REGIONE}/p-{pagina}"
            print(f"Visito pagina {pagina}: {url}")
            await page.goto(url)
            await page.wait_for_load_state('networkidle')

            elements = await page.query_selector_all("div.search-itm.js-shiny-data-user")
            print(f"  → Trovati {len(elements)} risultati in pagina {pagina}")

            hrefs = []
            for el in elements:
                div_info = await el.query_selector("div.search-itm__info")
                if div_info:
                    link = await div_info.query_selector("a")
                    if link:
                        href = await link.get_attribute("href")
                        if href:
                            hrefs.append(href)

            for href in hrefs:
                print(f"    → Apro {href}")
                try:
                    await page.goto(href, timeout=10000)
                    await page.wait_for_load_state('networkidle')
                except Exception as e:
                    print(f"  ⚠️  Errore durante apertura {href}: {e}")
                    continue

                nome_elem = await page.query_selector('span.scheda-azienda__companyTitle_content')
                if nome_elem:
                    nome = await nome_elem.inner_text()
                else:
                    nome_elem = await page.query_selector('h1.scheda-azienda__companyTitle')
                    nome = await nome_elem.inner_text() if nome_elem else "N/A"

                sito_elem = await page.query_selector('a.bttn.bttn--white[title^="sito web"]')
                sito = await sito_elem.get_attribute("href") if sito_elem else "N/A"

                if sito and "facebook.com" in sito.lower():
                    sito = "N/A"

                azienda = {"nome": nome}


                if sito != "N/A":
                    print(f"→ Analizzo sito: {sito}")
                    valutazione = 0
                    try:
                        await page.goto(sito)
                        await page.wait_for_load_state('load')
                        azienda["sito"] = sito

                        responsive = await valuta_responsivita(page)
                        if responsive:
                            valutazione += 35

                        azienda["valutazione"] =  valutazione

                    except Exception as e:
                        print(f"Errore durante l'apertura del sito {sito}: {e}")
                        azienda["sito"] = sito
                else:
                    azienda["sito"] = "N/A"
                    azienda["valutazione"] = 0

                risultati.append(azienda)

        await browser.close()

# Avvia lo script
asyncio.run(main())

# Scrittura su Excel con intestazioni formattate
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
        max_length = max(df[value].astype(str).map(len).max(), len(value))
        worksheet.set_column(col_num, col_num, max_length + 5)

    worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)