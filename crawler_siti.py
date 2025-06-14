# controlli_sito.py

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

    # True se almeno 3 su 5
    return punteggio >= 3
