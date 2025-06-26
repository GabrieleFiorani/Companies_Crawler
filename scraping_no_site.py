import requests
from bs4 import BeautifulSoup
import json
import time
import subprocess

# --- DuckDuckGo Search ---
def cerca_su_duckduckgo(query):
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0"}
    data = {"q": query}

    response = requests.post(url, data=data, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    risultati = []
    for result in soup.find_all("a", class_="result__a", limit=3):
        titolo = result.get_text()
        link = result.get("href")
        risultati.append((titolo, link))

    return risultati

# --- Verifica dominio ---
def dominio_verificabile(nome_azienda, url):
    nome = nome_azienda.lower().replace(" ", "").replace(".", "").replace(",", "").replace("-", "")
    dominio = url.split("//")[-1].split("/")[0].lower()
    if any(x in dominio for x in ["facebook", "wixsite", "blogspot", "youtube", "linkedin"]):
        return False
    return nome[:6] in dominio

# --- Verifica contenuto sito ---
def verifica_contenuto_sito(url, nome_azienda):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return False
        soup = BeautifulSoup(r.text, "html.parser")
        testo = soup.get_text().lower()
        nome_norm = nome_azienda.lower().split()[0]

        if "partita iva" in testo or "p.iva" in testo:
            return True
        if nome_norm in testo:
            return True
        return False
    except:
        return False

# --- Controllo finale ---
def sito_probabilmente_autentico(azienda, url):
    return dominio_verificabile(azienda, url) and verifica_contenuto_sito(url, azienda)

# --- Caricamento dati JSON ---
with open("aziende_senza_sito.json", "r", encoding="utf-8") as f:
    aziende_senza_sito = json.load(f)

with open("aziende_con_sito.json", "r", encoding="utf-8") as f:
    aziende_con_sito = json.load(f)

# --- Trasforma liste in dizionari per evitare duplicati ---
verificati_dict = {a["nome"]: a for a in aziende_con_sito}
nonverificati_dict = {}

# --- Ciclo principale ---
for azienda in aziende_senza_sito:
    nome = azienda["nome"]
    risultati = cerca_su_duckduckgo(nome)

    sito_trovato = False

    if risultati:
        for _, link in risultati:
            if sito_probabilmente_autentico(nome, link):
                verificati_dict[nome] = {"nome": nome, "sito": link}
                sito_trovato = True
                break

    if not sito_trovato:
        nonverificati_dict[nome] = {"nome": nome, "sito": "N/A"}

    time.sleep(2)

# --- Scrivi risultati su file JSON ---
with open("aziende_con_sito.json", "w", encoding="utf-8") as f:
    json.dump(list(verificati_dict.values()), f, indent=2, ensure_ascii=False)

with open("aziende_senza_sito.json", "w", encoding="utf-8") as f:
    json.dump(list(nonverificati_dict.values()), f, indent=2, ensure_ascii=False)


print("Parto con il terzo script...")
subprocess.run(["python", "crawler_siti.py"])
print("Terzo script terminato")