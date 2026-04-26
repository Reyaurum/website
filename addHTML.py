from pathlib import Path

dir = Path().resolve()

REPLACEMENT = [["""<nav class="nav">""", """<nav class="nav">
                <button class="menu-btn" id="menu_page">⇐</button>"""], ["""Next <span class="arrow">→</span>
                </button>
                </div>""", """Next <span class="arrow">→</span>
                </button>
                </div>
                <div class="menu-btn"></button>"""]]

def writeFile(html : str, ch : int):
    with open(dir.joinpath(f"ch-{ch}").joinpath(f"index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def getHtml(ch : int):
    with open(dir.joinpath(f"ch-{ch}").joinpath("index.html"), "r", encoding="utf-8") as f:
        return f.read()

def replaceHtml(ch : int):
    html = getHtml(ch)
    for rep in REPLACEMENT:
        if html.find(rep[1]) == -1:
            html = html.replace(rep[0], rep[1])
    writeFile(html, ch)

def main():
    start = int(input("Starting Chapter: "))
    end = int(input("Ending Chapter: "))
    for ch in range(start, end + 1):
        replaceHtml(ch)

if __name__ == "__main__":
    main()