import deepl
import os
from bs4 import BeautifulSoup
from requests import Session, RequestException
from pathlib import Path
from requests import Session, RequestException
from re import sub
from json import load, dump
from time import sleep
from dotenv import load_dotenv

load_dotenv()
DIR = Path().resolve()
DATA_FILEPATH = DIR.joinpath("data", "data.json")
DEEPL_CLIENT = deepl.DeepLClient(os.getenv("API_KEY"))

def getEnglishChapterTitle(ch : int):
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

    title = soup.find(id = "article").find("h4").text
    title = title[title.find(":") + 2:]
    print(title)
    return title
    
def getTranslatedTitle(ch : int):
    en_title = getEnglishChapterTitle(ch)
    jp_title = str(DEEPL_CLIENT.translate_text(en_title, source_lang="EN", target_lang="JA", model_type="quality_optimized", tag_handling="html", tag_handling_version="v2", preserve_formatting=True))

    print(jp_title)
    return jp_title

def updateChapterTitleData(ch : int):
    with open(DATA_FILEPATH, "r", encoding="UTF-8") as f:
        data = load(f)

    if len(data["chapter_titles"]) < ch:
        while len(data["chapter_titles"]) < ch:
            data["chapter_titles"].append("")
    data["chapter_titles"][ch - 1] = getTranslatedTitle(ch)
    
    with open(DATA_FILEPATH, "w", encoding="utf-8") as f:
        dump(data, f, indent=2)

def main():
    start_ch = int(input("Starting Chapter: "))
    end_ch = int(input("Ending Chapter: "))
    for ch in range(start_ch, end_ch + 1):
        print(f"\n --- Ch-{ch} ---")
        updateChapterTitleData(ch)
        sleep(2)

if __name__ == "__main__":
    main()