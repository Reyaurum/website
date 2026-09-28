import deepl
import os
from time import sleep
from bs4 import BeautifulSoup
from requests import Session, RequestException
from pathlib import Path
from requests import Session, RequestException
from re import sub
from json import load, dump
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote

load_dotenv()
DIR = Path().resolve()
DATA_FILEPATH = DIR.joinpath("data", "data.json")
deepl_client = deepl.DeepLClient(os.getenv("API_KEY"))

def getBaseText(ch : int):
    text = ["", ""] 
    url = f"https://freewebnovel.com/novel/shadow-slave/chapter-{ch}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://freewebnovel.com/",
    }
    session = Session()

    try:
        response = session.post(url, headers=headers)
        response.raise_for_status()
    except RequestException as e:
        raise Exception(f"Request Error: {e}")
    res = response.text
    soup = BeautifulSoup(res, "html.parser")

    for p in soup.find(id = "article").find_all("p"):
        text[0] += p.text[1:] + "\n\n"
    text[1] = soup.find(id = "article").find("h4").text
    text[1] = text[1][text[1].find(":") + 2:]
    print(f"Successfully Scraped Ch-{ch} : {text[1]}")
    return text

def updateChapterTitleData(title : str, ch : int):
    with open(DATA_FILEPATH, "r", encoding="UTF-8") as f:
        data = load(f)

    if len(data["chapter_titles"]) < ch:
        while len(data["chapter_titles"]) < ch:
            data["chapter_titles"].append("")
    data["chapter_titles"][ch - 1] = title
    
    with open(DATA_FILEPATH, "w", encoding="utf-8") as f:
        dump(data, f, indent=2)

def createTranslatedFile(ch : int):
    en_text = getBaseText(ch)
    res = deepl_client.translate_text(en_text, source_lang="EN", target_lang="JA", model_type="quality_optimized", tag_handling="html", tag_handling_version="v2", preserve_formatting=True)
    jp_text = str(res[0]).replace("……", "…")
    jp_text = sub(r'[\r\n\u2028\u2029\u0085\x0b\x0c]+', '\n\n', jp_text)

    with open(DIR.joinpath("text", f"Ch-{ch}.txt"), "w", encoding="utf-8") as f:
        f.write(jp_text)

    updateChapterTitleData(str(res[1]), ch)
    print(f"Successfully Translated Ch-{ch} : {str(res[1])}")

def makeSession():
    session = Session()
    retries = Retry(
        total=5,
        backoff_factor=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def searchJisho(query):
    url = f"https://jisho.org/search/{quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://jisho.org/",
    }
    session = makeSession()
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except RequestException as e:
        raise Exception(f"Request Error: {e}")
    return response.text

def getBoilerPlate():
    with open(DIR.joinpath("boilerplate.txt"), "r", encoding="utf-8") as f:
        text = f.read()
    return text

def getNewlines(text : str):
    pos = 0
    amount = 0
    newlines = []
    while text.find("\n", pos + 1) != -1:
        pos = text.find("\n", pos + 1)
        newlines.append(pos - amount)
        amount += 1
    return newlines

def searchText(text : str):
    text = text.replace("\n", "").replace(" ", "")
    html = searchJisho(text)
    soup = BeautifulSoup(html, "html.parser")
    return soup.find("section", {"id": "zen_bar"}).find_all("ul", recursive=False)
    
def getBody(text : str):
    sentences = []
    pos_start = 0
    increase = 400
    reduction = 0
    pos_end = increase
    while pos_start < len(text):
        while(True):
            try:
                pos_end = text.find("\n", pos_end+1 - reduction)
                pos_end = len(text) if pos_end == -1 else pos_end
                print(len(text), pos_start, pos_end, reduction, increase)
                if len(text[pos_start : pos_end].replace("\n", "").replace(" ", "")) == 0:
                    pos_start = len(text)
                    break
                sentences.extend(searchText(text[pos_start : pos_end].replace("\n", "").replace(" ", "")))
                pos_start = pos_end
                pos_end += increase
                reduction = 0
                break
            except:
                print("Retrying")
                reduction += 150
    return sentences

def getText(ch : int):
    with open(DIR.joinpath("text", f"Ch-{ch}.txt"), "r", encoding="utf-8") as f:
        text = f.read()
    return text.replace(" ", "").replace(".", "")

def addBody(html : str, ch : int):
    text = getText(ch)
    sentences = getBody(text)
    newlines = getNewlines(text)
    body = ""
    insertions = []
    char = 0
    for s in sentences:
        for w in s.find_all("span", {"class": "japanese_word__text_wrapper"}):
            for _ in w.text.replace("\n", "").replace(" ", ""):
                char += 1
                if char in newlines:
                    insertions.append(w.parent)
    for li in insertions:
        li.insert_after(BeautifulSoup("<br>", "html.parser").br)
        li.insert_after(BeautifulSoup("<br>", "html.parser").br)

    for s in sentences:
        body += str(s)
    body = body.replace("<a", "<div").replace("</a>", "</div>")
    html = html.replace('Ch-', f'Ch-{ch}')
    html = html.replace('id="Numeral">', f'id="Numeral">{ch}')
    body_pos = html.find('<div class="text_content">') + 26
    return html[:body_pos] + body + html[body_pos:]

def createIndexFile(html : str, ch : int):
    folder = DIR.joinpath(f"ch-{ch}")
    if not folder.exists():
        folder.mkdir()
    with open(folder.joinpath(f"index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Successfully Created Ch-{ch}/index.html")

def updateMaxChapterData(ch : int):
    with open(DATA_FILEPATH, "r", encoding="UTF-8") as f:
        data = load(f)
    data["total_chapters"] = ch if ch > data["total_chapters"] else data["total_chapters"]
    with open(DATA_FILEPATH, "w", encoding="utf-8") as f:
        dump(data, f, indent=2)

def main():
    start_ch = int(input("Starting Chapter: "))
    end_ch = int(input("Ending Chapter: "))
    boilerplate = getBoilerPlate()
    for ch in range(start_ch, end_ch + 1):
        print(f"\n --- Ch-{ch} ---")
        createTranslatedFile(ch)
        createIndexFile(addBody(boilerplate, ch), ch)
        updateMaxChapterData(ch)

if __name__ == "__main__":
    main()