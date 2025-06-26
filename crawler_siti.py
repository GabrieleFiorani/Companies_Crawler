import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import json

# --- Funzioni di controllo ---

def contiene_banner_cookie(soup):
    """Controlla se il sito mostra banner cookie"""
    keywords = ['cookie', 'consent', 'gdpr', 'privacy']
    for div in soup.find_all(['div', 'section', 'footer']):
        id_class = (div.get('id') or '') + ' ' + ' '.join(div.get('class', []))
        id_class = id_class.lower()
        if any(keyword in id_class for keyword in keywords):
            return True
    return False

def contiene_script_cookie(soup):
    """Controlla se nel sito sono presenti script di gestione cookie"""
    for script in soup.find_all('script'):
        src = script.get('src', '').lower() if script.has_attr('src') else ''
        if any(x in src for x in ['cookieconsent', 'tarteaucitron', 'cookie']):
            return True
    return False

def SEO_check(soup):
    """Valuta alcuni elementi SEO basilari, ritorna True se almeno 5 punti su 7"""
    points = 0

    # Titolo
    title = soup.find('title')
    if title and len(title.text) > 0:
        points += 1

    # Descrizione meta
    description = soup.find('meta', attrs={'name': 'description'})
    if description and 'content' in description.attrs and len(description['content']) > 0:
        points += 1

    # H1
    h1_tags = soup.find_all('h1')
    if len(h1_tags) > 0:
        points += 1

    # Canonical link
    if soup.find('link', rel='canonical'):
        points += 1

    # Almeno un link
    if soup.find('a', href=True):
        points += 1

    # Presenza immagini
    images = soup.find_all('img')
    if len(images) > 0:
        points += 1

    # Almeno un'immagine con alt
    for img in images:
        if img.has_attr('alt') and len(img['alt']) > 0:
            points += 1
            break

    return points >= 5

def controllo_performance(url, max_tempo=3, max_dimensione_kb=500):
    """Controlla se la pagina risponde entro max_tempo e pesa meno di max_dimensione_kb"""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        start = time.time()
        response = requests.get(url, timeout=10, headers=headers)
        durata = time.time() - start

        if response.status_code != 200:
            return False

        dimensione_kb = len(response.content) / 1024

        return durata <= max_tempo and dimensione_kb <= max_dimensione_kb
    except:
        return False


def controllo_https_solo_protocollo(url):
    return url.lower().startswith("https://")


def presenza_contatti(soup):
    """Controlla se nella pagina ci sono riferimenti ai contatti"""
    testo = soup.get_text(separator=' ').lower()
    parole_chiave = ['contatti', 'contact', 'telefono', 'email', 'indirizzo', 'tel', 'cellulare']

    if any(parola in testo for parola in parole_chiave):
        return True

    mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
    if mailto:
        return True

    tel = soup.find('a', href=re.compile(r'^tel:', re.I))
    if tel:
        return True

    telefono_regex = re.compile(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?){1,3}\d{3,4}')
    if telefono_regex.search(testo):
        return True

    return False

def presenza_partita_iva(soup):
    """Controlla se la pagina contiene partita IVA"""
    testo = soup.get_text(separator=' ').lower()
    pattern = re.compile(r'partita iva[:\s]*([0-9]{11})', re.I)
    if pattern.search(testo):
        return True
    pattern_num = re.compile(r'\b[0-9]{11}\b')
    if pattern_num.search(testo):
        return True
    return False

def check_viewport_meta(soup):
    """Controlla se il meta viewport è presente e configurato correttamente"""
    viewport = soup.find('meta', attrs={"name": "viewport"})
    if viewport and viewport.has_attr('content'):
        content = viewport['content'].lower()
        if 'width=device-width' in content and 'initial-scale=1' in content:
            return True
    return False

def has_media_queries(url, verbose=False, retries=3):
    """
    Controlla la presenza di media queries nella pagina.
    Usa Selenium per eseguire il JS e caricare dinamicamente la pagina.
    Effettua retry in caso di fallimenti o contenuti incompleti.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
    )
    service = Service(log_path='nul')  # Windows

    for attempt in range(retries):
        if verbose:
            print(f"Attempt {attempt + 1} to check media queries on {url}")
        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)

            # Attendi caricamento completo del DOM
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            # Attendi che almeno un file CSS sia caricato (presenza di link o style)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "link[rel='stylesheet'], style"))
                )
            except TimeoutException:
                if verbose:
                    print("Timeout attesa file CSS.")
                # Continua comunque

            # Attendi un po' per eventuali caricamenti JS dinamici aggiuntivi
            time.sleep(3)

            # Controlla la URL finale (dopo eventuali redirect)
            final_url = driver.current_url
            if verbose and final_url != url:
                print(f"Redirect da {url} a {final_url}")

            # Parsing HTML con BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            media_query_regex = re.compile(r'@media[^{]+{')

            # Cerca media queries inline nei tag style
            for style_tag in soup.find_all("style"):
                if style_tag.string and media_query_regex.search(style_tag.string):
                    if verbose:
                        print("Media query trovata inline.")
                    driver.quit()
                    return True

            # Cerca media queries nei CSS esterni
            css_links = [link.get('href') for link in soup.find_all("link", rel="stylesheet") if link.get('href')]

            for css_link in css_links:
                full_url = css_link
                if not css_link.startswith("http"):
                    full_url = requests.compat.urljoin(final_url, css_link)
                try:
                    resp = requests.get(full_url, timeout=7)
                    if resp.status_code == 200 and media_query_regex.search(resp.text):
                        if verbose:
                            print(f"Media query trovata in {full_url}")
                        driver.quit()
                        return True
                except requests.RequestException:
                    if verbose:
                        print(f"Errore nel caricamento del CSS: {full_url}")
                    continue

            driver.quit()
            if verbose:
                print("Nessuna media query trovata.")
            return False

        except WebDriverException as e:
            if verbose:
                print(f"Errore WebDriver: {e}")
            try:
                driver.quit()
            except:
                pass
            time.sleep(2)  # aspetta prima di retry

    # Se arriviamo qui, tutti i tentativi sono falliti
    if verbose:
        print("Tutti i tentativi falliti per has_media_queries.")
    return False

# --- Funzione principale di controllo sito ---

def site_checker(url, verbose=False):
    """
    Valuta un sito su vari parametri (cookie, SEO, performance, contatti, partita IVA, responsive).
    Ritorna una percentuale di "qualità" su 100%.
    """
    max_points = 9
    points = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            if verbose:
                print(f"Status code {response.status_code} per {url}")
            return "0%"

        soup = BeautifulSoup(response.text, 'html.parser')

        # HTTPS bonus
        if url.startswith("https://"):
            points += 0.5

        # Footer esiste
        footer = soup.find('footer')
        if not footer:
            footer = soup.find('div', {'id': lambda x: x and 'footer' in x.lower()})

        if footer:
            points += 0.5

        # Banner cookie o script cookie
        if contiene_banner_cookie(soup) or contiene_script_cookie(soup):
            points += 0.5

        # SEO
        if SEO_check(soup):
            points += 1

        # Performance
        if controllo_performance(url):
            points += 1

        # Contatti
        if presenza_contatti(soup):
            points += 1

        # Partita IVA
        if presenza_partita_iva(soup):
            points += 0.5

        # Meta viewport
        if check_viewport_meta(soup):
            points += 0.5

        # Media queries / responsive
        if has_media_queries(url, verbose=verbose):
            points += 3
        
        # Controllo HTTPS
        if controllo_https_solo_protocollo(url):
            points += 0.5

        percent = round(points / max_points * 100)
        if verbose:
            print(f"Punteggio totale: {points} / {max_points} => {percent}%")
        return f"{percent}%"

    except Exception as e:
        if verbose:
            print(f"Errore generale su {url}: {e}")
        return "0%"

# --- Esempio di utilizzo ---

import json

# Carica il file esistente
with open("aziende_con_sito.json", "r", encoding="utf-8") as f:
    aziende = json.load(f)

# Applica la funzione site_checker a ciascuna azienda
for azienda in aziende:
    nome = azienda['nome']
    sito = azienda['sito']
    try:
        risultato = site_checker(sito)
    except Exception as e:
        risultato = "Errore: " + str(e)  # oppure risultato = 0
    azienda['percentuale'] = risultato

# Sovrascrivi lo stesso file con i dati aggiornati
with open("aziende_con_sito.json", "w", encoding="utf-8") as f_out:
    json.dump(aziende, f_out, ensure_ascii=False, indent=2)