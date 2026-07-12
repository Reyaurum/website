import deepl
from requests import get, Session, RequestException
from bs4 import BeautifulSoup
from pathlib import Path 

auth_key = "47c4aca4-cf92-4553-ab37-b8eed062a5f8:fx"
deepl_client = deepl.DeepLClient(auth_key)


dir = Path(__file__).parent

def scrape(cur_ch : int):
    text = ""
    file_path = f"{dir}\\text\\Ch-{cur_ch}.txt"
    url = f"https://freewebnovel.com/novel/shadow-slave/chapter-{cur_ch}"

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

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")
    for p in soup.find(id = "article").find_all("p"):
        text += p.text[1:] + "\n"
    text = text.replace("…", "...")
    with open(file_path, "a", errors="ignore") as f:
        f.write(text)
    
def createTranslatedFile(cur_ch : int):
    file_path = f"{dir}\\text\\Ch-{cur_ch}.txt"
    with open(file_path, "r") as f:
        en_text = f.read()
    jp_text = deepl_client.translate_text(en_text, source_lang="EN", target_lang="JA", model_type="quality_optimized", tag_handling="html", tag_handling_version="v2")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(jp_text))
    print(str(jp_text))
    print(file_path)


def main():
    cur_ch = int(input("Starting Chapter: "))
    end_ch = int(input("Ending Chapter: "))
    while cur_ch <= end_ch:
        scrape(cur_ch)
        createTranslatedFile(cur_ch)
        cur_ch += 1

if __name__ == "__main__":
    main()