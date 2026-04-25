from bs4 import BeautifulSoup
from requests import Session, RequestException
from pathlib import Path

sentences = []
dir = Path().resolve()

def searchJisho(query):
    url = "https://jisho.org/search"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0"
    }
    data = {
        "keyword": query
    }
    session = Session()

    try:
        response = session.post(url, headers=headers, data=data)
        response.raise_for_status()
    except RequestException as e:
        raise Exception(f"Request Error: {e}")
    return response.text

def getBoilerPlate():
    with open(dir.joinpath("boilerplate.txt"), "r", encoding="utf-8") as f:
        text = f.read()
    return text

def getNewlines(text : str):
    pos = 0
    amount = 0
    newlines = []
    while text.find("\n", pos+2) != -1:
        pos = text.find("\n", pos+2)
        newlines.append(pos - amount)
        amount += 2
    return newlines

def searchText(text : str):
    text = text.replace("\n", "").replace(" ", "")
    html = searchJisho(text)
    soup = BeautifulSoup(html, "html.parser")
    sentences.extend(soup.find("section", {"id": "zen_bar"}).find_all("ul", recursive=False))
    
def getBody(text : str):
    pos_start = 0
    pos_end = 1600
    while text.find("\n", pos_end+1) != -1:
        pos_end = text.find("\n", pos_end+1)
        searchText(text[pos_start : pos_end].replace("\n", "").replace(" ", ""))
        pos_start = pos_end
        pos_end += 1600
    pos_end = len(text)
    searchText(text[pos_start : pos_end].replace("\n", "").replace(" ", ""))

def getText(ch : int):
    with open(dir.joinpath("text", f"Ch-{ch}.txt"), "r", encoding="utf-8") as f:
        text = f.read()
    return text.replace(" ", "").replace(".", "")

def addBody(html : str, ch : int):
    text = getText(ch)
    getBody(text)
    newlines = getNewlines(text)
    body = ""
    insertions = []
    char = 0
    for s in sentences:
        for w in s.find_all("span", {"class": "japanese_word__text_wrapper"}):
            for c in w.text.replace("\n", "").replace(" ", ""):
                char += 1
                if char in newlines:
                    insertions.append(w.parent)
    for li in insertions:
        li.insert_after(BeautifulSoup("<br>", "html.parser").br)
        li.insert_after(BeautifulSoup("<br>", "html.parser").br)

    for s in sentences:
        body += str(s)
    body = body.replace("<a", "<div").replace("</a>", "</div>")
    html = html.replace('Ch-1', f'Ch-{ch}')
    html = html.replace('id="Numeral">1', f'id="Numeral">{ch}')
    body_pos = html.find('<div class="text_content">') + 26
    return html[:body_pos] + body + html[body_pos:]

def createFile(html : str, ch : int):
    folder = dir.joinpath(f"ch-{ch}")
    if not folder.exists():
        folder.mkdir()
    with open(folder.joinpath(f"index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def getFile(start : int, end : int):
    boilerplate = getBoilerPlate()
    for ch in range(start, end + 1):
        print(f"Creating Chapter-{ch}")
        createFile(addBody(boilerplate, ch), ch)
        print(f"Chapter-{ch} complete")

if __name__ == "__main__":
    start_ch = int(input("Starting Chapter: "))
    end_ch = int(input("Ending Chapter: "))
    getFile(start_ch, end_ch)