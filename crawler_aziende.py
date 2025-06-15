import asyncio
import subprocess
import json
from playwright.async_api import async_playwright

NUM_PAGINE = int(input("Quante pagine vuoi visitare?: "))
REGIONE = input("Digita la regione per la ricerca (es. Lombardia, Lazio, etc.): ")

aziende_con_sito = []
aziende_senza_sito = []

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

                if sito and any(social in sito.lower() for social in ["facebook.com", "instagram.com"]):
                    sito = "N/A"

                azienda = {"nome": nome}

                if sito != "N/A":
                    azienda["sito"] = sito
                    aziende_con_sito.append(azienda)
                else:
                    azienda["sito"] = "N/A"
                    aziende_senza_sito.append(azienda)

        await browser.close()

    # 🔽 Dopo la chiusura del browser, salviamo i JSON
    with open("aziende_con_sito.json", "w", encoding="utf-8") as f:
        json.dump(aziende_con_sito, f, ensure_ascii=False, indent=2)

    with open("aziende_senza_sito.json", "w", encoding="utf-8") as f:
        json.dump(aziende_senza_sito, f, ensure_ascii=False, indent=2)

    print("✅ File JSON salvati.")

# 🔽 Esegui main
asyncio.run(main())
# 🔽 Ora lanciamo il secondo script
print("Parto con il secondo script...")
subprocess.run(["python", "crawler_siti.py"])
print("Secondo script terminato")