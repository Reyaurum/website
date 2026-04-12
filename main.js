let kana = [
"あ","い","う","え","お",
"か","き","く","け","こ",
"さ","し","す","せ","そ",
"た","ち","つ","て","と",
"な","に","ぬ","ね","の",
"は","ひ","ふ","へ","ほ",
"ま","み","む","め","も",
"や","ゆ","よ",
"ら","り","る","れ","ろ",
"わ","を","ん",

"が","ぎ","ぐ","げ","ご",
"ざ","じ","ず","ぜ","ぞ",
"だ","ぢ","づ","で","ど",
"ば","び","ぶ","べ","ぼ",
"ぱ","ぴ","ぷ","ぺ","ぽ",

"ぁ","ぃ","ぅ","ぇ","ぉ",
"ゃ","ゅ","ょ","っ","ゎ",

"ア","イ","ウ","エ","オ",
"カ","キ","ク","ケ","コ",
"サ","シ","ス","セ","ソ",
"タ","チ","ツ","テ","ト",
"ナ","ニ","ヌ","ネ","ノ",
"ハ","ヒ","フ","ヘ","ホ",
"マ","ミ","ム","メ","モ",
"ヤ","ユ","ヨ",
"ラ","リ","ル","レ","ロ",
"ワ","ヲ","ン",

"ガ","ギ","グ","ゲ","ゴ",
"ザ","ジ","ズ","ゼ","ゾ",
"ダ","ヂ","ヅ","デ","ド",
"バ","ビ","ブ","ベ","ボ",
"パ","ピ","プ","ペ","ポ",

"ァ","ィ","ゥ","ェ","ォ",
"ャ","ュ","ョ","ッ","ヮ",

"ヴ","ヵ","ヶ"
];
const replacements = ["う", "く", "ぐ", "す", "つ", "ぬ", "ぶ", "む", "る", "い", ""]
let data = null;
const index = new Map();
let m_pos;

function initResize() {
    let resize_el = document.getElementById("dictionary_body");
    resize_el.addEventListener("pointerdown", function(e){
        let style = window.getComputedStyle(document.querySelector("#dictionary_navbar"))
        let navbar_height = parseInt(style.marginTop) + parseInt(style.marginBottom) + parseInt(style.height)
        
        if (window.innerHeight - e.y - document.querySelector("#dictionary_body").offsetHeight + navbar_height > 0) {
            document.body.className = "unselectable"
            document.querySelector("#dictionary_body").style.overflowY = "hidden"
            m_pos = e.y
            document.addEventListener("pointermove", resize, {passive: false}, false);
        }
    }, false);

    document.addEventListener("pointerup", function(){
        document.body.className = ""
        document.querySelector("#dictionary_body").style.overflowY = "scroll"
        document.removeEventListener("pointermove", resize, {passive: false}, false);
    }, false);
}

function resize(e){
    e.preventDefault()
    let dx = 0;
    let resize_el = document.getElementById("dictionary_body");
    let style = window.getComputedStyle(document.querySelector("#dictionary_navbar"))
    let navbar_height = parseInt(style.marginTop) + parseInt(style.marginBottom) + parseInt(style.height)
    dx = m_pos - e.y
    m_pos = e.y
    resize_el.style.height = (parseInt(getComputedStyle(resize_el, '').height) + dx) + "px";
    let height = parseInt(resize_el.style.height);
    height < navbar_height ? resize_el.style.height = navbar_height + "px" : (height > window.innerHeight ? resize_el.style.height = window.innerHeight + "px" : null)
}

async function getData() {
    const res = await fetch("/website/data/data.b64")
    const base64 = await res.text()

    const binary = atob(base64);
    const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));

    const decompressed = await new Response(
        new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
    ).text();

    data = JSON.parse(decompressed);

    data.forEach(entry => {
        entry.r.forEach(r => index.set(r, entry));
        entry.k.forEach(k => index.set(k, entry));
    });
}

function length(text) {
    let len = 0;
    for (let i = 0; i < text.length; i++) {
        if (!kana.includes(text[i])) len += 2;
        else if (text[i] !== "っ") len++;
    }
    return len;
}

function sort(map) {
    return [...map]
        .sort((a, b) => {
            const aVal = a.k.length + a.r.length + a.m.length;
            const bVal = b.k.length + b.r.length + b.m.length;
            return bVal - aVal; // descending
        })
        .sort((a, b) => {
            if (a.k.length === 0) return -1;
            if (b.k.length === 0) return 1;
            return 0;
        });
}

function searchReading(query, reading = "") {
    return data.filter(entry =>
        entry.k.some(k => k === query) &&
        entry.r.some(r => reading ? r.includes(reading) : true)
    );
}

function searchParticle(query) {
    return data.filter(entry =>
        entry.r.some(r => r === query)
    );
}

function testVariations(query, reading = "", len) {
    return data.filter(entry => {
        return entry.k.some(k => {
            if (!(k.length <= len + 1 && k.length > 1)) return false;

            return replacements.some(rep => {
                const kMatch = k.includes(query + rep);

                const rMatch = entry.r.some(r => {
                    if (!reading) return true;
                    return (
                        r.includes(reading + rep) &&
                        r.length <= length(reading + rep)
                    );
                });

                return kMatch && rMatch;
            });
        });
    });
}

function testVariationKana(query) {
    return data.filter(entry =>
        entry.k.some(k => k.length > 1 && kana.includes(k[1])) &&
        replacements.some(rep =>
            entry.r.some(r =>
                r.includes(query + rep) &&
                r.length <= length(query + rep)
            )
        )
    );
}

async function searchKanji(text) {
    let res = [];

    for (let i = 1; i <= text.length; i++) {
        for (let k = 0; k < i; k++) {
            const char = text.substring(k, k + text.length - i + 1);

            let r = index.get(char);

            if (!r) {
                r = data.find(entry =>
                    entry.k.some(k =>
                        k[0] === char &&
                        kana.includes(k[1]) &&
                        (k.length >= 3 ? kana.includes(k[2]) : true)
                    )
                );
            }

            if (r) res.push(r);
        }
    }

    return res;
}

function searchVerb(text, reading = "") {
    let res = [];

    let baseText = text;
    let baseReading = reading;

    let len = 0;

    for (let i = 0; i < baseText.length; i++) {
        if (
            kana.includes(baseText[i]) &&
            (baseText.length > 3 ? kana.includes(baseText[i + 1]) : true)
        ) break;

        len++;
    }

    while (res.length === 0 && baseText.length >= 1) {
        if (len) {
            res = testVariations(baseText, baseReading, len + 1);
        } else {
            res = testVariationKana(baseText);
        }

        let remove = baseText.endsWith("かった") ? 3 : 1;

        baseText = baseText.slice(0, -remove);
        if (baseText.endsWith("っ")) {
            baseText = baseText.slice(0, -1);
        }

        remove = baseReading.endsWith("かった") ? 3 : 1;

        baseReading = baseReading.slice(0, -remove);
        if (baseReading.endsWith("っ")) {
            baseReading = baseReading.slice(0, -1);
        }
    }

    return res;
}

async function search(text, reading = "") {
    let res = [];

    res = searchReading(text, reading);

    if (res.length === 0) {
        res = searchReading(text);
    }

    if (res.length === 0) {
        res = searchParticle(text);
    }

    if (res.length === 0) {
        res = searchVerb(text, reading);
    }

    if (res.length === 0) {
        res = await searchKanji(text);
    }

    return sort(res);
}

function createElement(tag, className, id="", text="") {
    let e = document.createElement(tag)
    className ? e.className = className : null
    id ? e.id = id : null
    text ? e.innerText = text : null
    return e
}

function createConcept(entry, reading) {
    let concept = createElement("div", "concept_light clearfix")
    let concept_wrapper = createElement("div", "concept_light-wrapper")
    let concept_readings = createElement("div", "concept_light-readings japanese_gothic")
    let concept_representation = createElement("div", "concept_light-representation")
    let furigana = createElement("span", "furigana")
    let kanji = createElement("span", "kanji", "", entry.r[0])
    let text = createElement("span", "text", "", (entry.k[0] ? entry.k[0] : reading))

    furigana.appendChild(kanji)
    concept_representation.appendChild(furigana)
    concept_representation.appendChild(text)
    concept_readings.appendChild(concept_representation)
    concept_wrapper.appendChild(concept_readings)

    let concept_meanings = createElement("div", "concept_light-meanings")
    let meanings_wrapper = createElement("div", "meanings_wrapper")
    let meaning_wrapper = createElement("div", "meaning_wrapper")
    let meaning_definition = createElement("div", "meaning-definition")
    let meaning_divider = createElement("span", "meaning-definition-section_divider", "", "1. ")
    let meaning_meaning = createElement("span", "meaning-meaning", "", entry.m.toString().replaceAll(",", ";  "))

    meaning_definition.appendChild(meaning_divider)
    meaning_definition.appendChild(meaning_meaning)
    meaning_wrapper.appendChild(meaning_definition)
    meanings_wrapper.appendChild(meaning_wrapper)
    concept_meanings.appendChild(meanings_wrapper)
    
    concept.appendChild(concept_wrapper)
    concept.appendChild(concept_meanings)

    document.querySelector("#concepts_holder").appendChild(concept)
}

function showDictionary(res, text, reading) {
    console.log(res)
    document.getElementById("concepts_holder").innerHTML = ""
    reading ? null : reading = text
    res.forEach((entry) => {
        createConcept(entry, reading)
    })
    document.getElementById("word_amount").innerText = `WORDS - ${document.getElementById("concepts_holder").childElementCount} FOUND`
}

async function searchDictionary(e) {
    var target = e.target || e.srcElement
    let particles = ["。", "、", "・", "…", "？", "！", "＊", "：", "『", "』", "「", "」"]
    try {
        if (target.classList[0] == "japanese_word__furigana" || particles.includes(target.innerText))
            return
        while (target.classList[0] != "japanese_word__text_wrapper") {
            target = target.parentNode
        }
        let sibling = target.previousElementSibling
        showDictionary(await search(target.innerText, sibling.innerText), target.innerText, sibling.innerText)
    } catch {}
}

function main() {
    getData()
    initResize()
    document.addEventListener("pointerdown", searchDictionary, false);
}

document.addEventListener("DOMContentLoaded", () => {
    main()
});