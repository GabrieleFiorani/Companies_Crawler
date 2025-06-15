# controlli_sito.py
import re
import asyncio
import json
from playwright.async_api import async_playwright



#controllo responsitività sito web
async def valuta_responsivita(page):
    """
    Controllo avanzato responsive.
    Restituisce True se almeno 3/5 controlli passano, altrimenti False.
    """

    punteggio = 0
    totale = 5

    # 1. Meta viewport presente
    if await page.query_selector('meta[name="viewport"]') is not None:
        punteggio += 1

    # 2. Nessun elemento sborda orizzontalmente
    no_overflow = await page.evaluate("""
        !Array.from(document.querySelectorAll('*')).some(el => {
            const rect = el.getBoundingClientRect();
            return rect.right > window.innerWidth;
        })
    """)
    if no_overflow:
        punteggio += 1

    # 3. Media queries nei CSS
    has_media_query = await page.evaluate("""
        Array.from(document.styleSheets).some(sheet => {
            try {
                return Array.from(sheet.cssRules || []).some(rule => rule.media && rule.media.mediaText);
            } catch (e) {
                return false;
            }
        });
    """)
    if has_media_query:
        punteggio += 1

    # 4. Simulazione viewport mobile/tablet/desktop
    resolutions = [
        {"width": 1920, "height": 1080},
        {"width": 1024, "height": 768},
        {"width": 375, "height": 667}
    ]
    passed = 0
    for res in resolutions:
        await page.set_viewport_size(res)
        await page.wait_for_timeout(500)
        no_scroll = await page.evaluate("document.body.scrollWidth <= window.innerWidth")
        if no_scroll:
            passed += 1
    if passed >= 2:
        punteggio += 1

    # 5. Usa framework responsivi noti (bootstrap, tailwind)
    uses_framework = await page.evaluate("""
        document.documentElement.innerHTML.includes('bootstrap') ||
        document.documentElement.innerHTML.includes('tailwind')
    """)
    if uses_framework:
        punteggio += 1

    return punteggio >= 3






#controllo header
async def has_header(page):
    return await page.query_selector("header") is not None




#controllo footer
async def has_footer(page):
    return await page.query_selector("footer") is not None




#controllo logo
async def has_logo(page):
    selettori_logo = [
        'img[class*="logo"]',
        'img[id*="logo"]',
        'img[src*="logo"]',
        'header img',
        'a[href="/"] img'
    ]
    for selector in selettori_logo:
        elemento = await page.query_selector(selector)
        if elemento:
            return True
    return False




#controllo informazioni di contatto
async def has_contact_info(page):
    contenuto = await page.content()
    
    # Controllo telefono (anche con prefisso +39)
    has_phone = re.search(r'(\+39\s?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}|\b\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}\b)', contenuto)
    
    # Controllo email
    has_email = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', contenuto)

    # Ritorna True solo se entrambi sono presenti
    return has_phone is not None and has_email is not None



# Controllo meta description
async def check_meta_description(page):
    try:
        meta = await page.query_selector('meta[name="description"]')
        if not meta:
            return False
        content = await meta.get_attribute('content')
        if content and 50 <= len(content) <= 160:
            return True
        return False
    except Exception:
        return False
    



# Controllo SEO
async def controlla_seo(page):
    punteggio = 0
    totale = 4

    # 1. Title valido (presente e lunghezza 10-70)
    title = await page.title()
    if title and 10 <= len(title) <= 70:
        punteggio += 1

    # 2. Meta description valida (presente e lunghezza 50-160)
    if await check_meta_description(page):
        punteggio += 1

    # 3. Esattamente un tag H1
    h1_tags = await page.query_selector_all("h1")
    if len(h1_tags) == 1:
        punteggio += 1

    # 4. Almeno il 90% delle immagini con attributo alt
    imgs = await page.query_selector_all("img")
    if imgs:
        imgs_senza_alt = 0
        for img in imgs:
            alt = await img.get_attribute("alt")
            if not alt:
                imgs_senza_alt += 1
        if imgs_senza_alt / len(imgs) <= 0.1:
            punteggio += 1
    else:
        # Se non ci sono immagini, consideriamo superato questo check
        punteggio += 1

    # Soglia minima: almeno 3 controlli superati
    return punteggio >= 3



# Controllo velocità di caricamento
async def check_velocita_caricamento(page, url, soglia=3.0):
    try:
        await page.goto(url, timeout=15000)
        durata = await page.evaluate("""
            () => {
                const timing = performance.timing;
                return (timing.loadEventEnd - timing.navigationStart) / 1000;
            }
        """)
        return durata <= soglia
    except Exception as e:
        print(f"Errore nel check velocità: {e}")
        return False
    


# Controllo se il sito ha SSL
def has_ssl(url):
    return url.startswith("https://")



# Controllo se il sito ha una mappa integrata
async def has_map(page):
    # 1. Cerca iframe di Google Maps o simili
    iframe_maps = await page.query_selector_all('iframe[src*="google.com/maps"], iframe[src*="maps.google.com"], iframe[src*="openstreetmap.org"]')
    if iframe_maps:
        return True

    # 2. Cerca elementi con id o class contenenti "map"
    map_elements = await page.query_selector_all('[id*="map"], [class*="map"]')
    if map_elements:
        return True

    # 3. Cerca script che caricano le API di Google Maps
    scripts = await page.query_selector_all('script[src*="maps.googleapis.com/maps/api"]')
    if scripts:
        return True

    return False



# Controllo se il sito ha link ai social
async def has_social_links(page):
    social_domains = ["facebook.com", "instagram.com", "linkedin.com", "twitter.com", "youtube.com"]
    links = await page.query_selector_all("a[href]")
    for link in links:
        href = await link.get_attribute("href")
        if href and any(domain in href for domain in social_domains):
            return True
    return False



# Controllo se il sito ha una privacy policy
async def has_privacy_policy(page):
    contenuto = await page.content()
    return ("privacy policy" in contenuto.lower() or "cookie policy" in contenuto.lower())



with open("aziende_con_sito.json", "r", encoding="utf-8") as f:
    aziende_con_sito = json.load(f)

async def analizza_siti(aziende_con_sito):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for azienda in aziende_con_sito:
            sito = azienda["sito"]
            print(f"Analizzo sito: {azienda['nome']} - {sito}")
            valutazione = 0
            try:
                await page.goto(sito, timeout=10000, wait_until='domcontentloaded')
                await page.wait_for_timeout(1000)  # breve attesa per sicurezza


                if await valuta_responsivita(page):
                    valutazione += 20
                if await has_header(page):
                    valutazione += 5
                if await has_footer(page):
                    valutazione += 5
                if await has_logo(page):
                    valutazione += 5
                if await has_contact_info(page):
                    valutazione += 5
                if await controlla_seo(page):
                    valutazione += 25
                if await check_velocita_caricamento(page, sito):
                    valutazione += 10
                if has_ssl(sito):
                    valutazione += 10
                if await has_map(page):
                    valutazione += 5
                if await has_social_links(page):
                    valutazione += 5
                if await has_privacy_policy(page):
                    valutazione += 5

                azienda["valutazione"] = f"{valutazione}%"
            except Exception as e:
                print(f"⚠️ Errore analizzando sito {sito}: {e}")
                azienda["valutazione"] = "Errore"

        await browser.close()

        print("\nRisultati analisi:")
        for azienda in aziende_con_sito:
            print(azienda)


asyncio.run(analizza_siti(aziende_con_sito))