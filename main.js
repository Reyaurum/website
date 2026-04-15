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
let hiragana = [
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
]
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
    let len = 0
    for (let i = 0; i < text.length; i++) {
        if (!kana.includes(text[i]))
            len += 2
        else if (text[i] != "っ")
            len++
        }
    return len
}

function sort(map) {
    let interupt = 0
    let current_value = null
    let next_value = null
    do {
        interupt = 0
        for (let i = 0; i < map.length - 1; i++) {
            current_value = map[i].k.length + map[i].r.length + map[i].m.length
            next_value = map[i + 1].k.length + map[i + 1].r.length + map[i + 1].m.length
            if (next_value > current_value) {
                current_value = map[i]
                map[i] = map[i + 1]
                map[i + 1] = current_value
                interupt = 1
            }
        }
    } while (interupt)
    for (let i = map.length - 1; i >= 0; i--) {
        if (map[i].k.length == 0) {
            current_value = map[i]
            for (let k = i; k > 0 ; k--) {
                map[k] = map[k - 1]
            }
            map[0] = current_value
        }
    }
    
    return map
}

function searchReading(query, reading="") {
    return data.filter(entry =>
        entry.k.some(k => k == query) &&
        entry.r.some(r => reading ? r.includes(reading) : true)
    );
}

function searchParticle(query) {
    return data.filter(entry =>
        entry.r.some(r => r == query)
    );
}

function testVariations(query, reading="", len) {
    let found = 0
    return data.filter(entry =>
        entry.k.some(k => k.length <= len + 1 && k.length > 1) &&
        replacements.some(rep => 
            entry.k.some(k => k.includes(query + rep)) &&
            entry.r.some(r => (reading ? r.includes(reading + (rep == "" && found ? "|" : rep)) : 1) && r.length <= length(reading + rep) && ++found)
        )
    );
}

function testVariationKana(query) {
    return data.filter(entry =>
        entry.k.some(k => k.length > 1 && kana.includes(k[1])) &&
        replacements.some(rep => 
            entry.r.some(r => r.includes(query + rep) && r.length <= length(query + rep))
        )
    );
}

function testVariationKanji(query) {
    return data.filter(entry =>
        !(entry.k.some(k => 
            k.length > query.length + 1
        )) &&
        entry.k.some(k => 
            k.length > 1 && kana.includes(k[1])
        ) &&
        replacements.some(rep => 
            entry.k.some(k => k.includes(query + rep) && k.length <= length(query + rep))
        )
    );
}

function searchKanji(text) {
    let res = [], char = "", r = null
    for (let i = 1; i <= text.length; i++) {
        for (let k = 0; k < i; k++) {
            char = text.substring(k, k + text.length - i + 1)
            r = index.get(char)
            r ? null : r = data.filter(entry => 
                entry.k.some(k => k[0] == char && kana.includes(k[1]) && (k.length >= 3 ? kana.includes(k[2]) : 1))
            )[0]
            r ? res = res.concat(r) : null
        }
    }
    return res
}

function getKanji(entry) {
    let res = []
    for (let c of entry)
        kana.includes(c) ? null : res = res.concat(c) 
    return res
}

function getMeanings(query) {    
    console.log(query)
    let meanings = []
    let res = data.filter(entry =>
        !entry.k.some(k => k.length >= 4) &&
        entry.k.some(k => k.includes(query)) &&
        !entry.k.some(k => {
            for (let c of k) {
                if (!hiragana.includes(c) && query != c)
                    return true
            } return false
        }));
    console.log(res)
    res.length == 0 ? res = res.concat(index.get(query)) : null
    console.log(res)
    res.length == 0 ? res = data.filter(entry =>
        !entry.k.some(k => k.length >= 4) &&
        entry.k.some(k => k.includes(query)) &&
        entry.k.some(k => {
            for (let c of k) {
                if (!hiragana.includes(c) && query != c)
                    return false
            } return true
        })) : null
    console.log(res)
    res.forEach((e) => {
        meanings = meanings.concat(e.m)   
    })
    meanings = [...new Set(meanings)].filter(m =>
        !m.includes("...") &&
        m.length <= 12
    )
    return (meanings.length ? meanings : index.get(query).m)
}

function searchVerb(text, reading="") {
    let res = [];
    let len = 0
    let remove = 0
    for (let i = 0; i < text.length; i++) {
        if (kana.includes(text[i]) && (text.length >= 2 ? kana.includes(text[i + 1]) : 1) && (text.length >= 3 ? kana.includes(text[i + 2]) : 1))
            break;
        len++
    }
    while (res.length == 0 && text.length >= 1) {
        if (res.length == 0) {
            len ? res = testVariations(text, reading, len + 1) : res = testVariationKana(text)
        }
        text.substring(text.length - 3, text.length) == "かった" ? remove = 3 : remove = 1
        text = text.substring(0, text.length - remove)
        text[text.length - 1] == "っ" ? text = text.substring(0, text.length - 1) : null
        reading.substring(reading.length - 3, reading.length) == "かった" ? remove = 3 : remove = 1
        reading = reading.substring(0, reading.length - remove)
        reading[reading.length - 1] == "っ" ? reading = reading.substring(0, reading.length - 1) : null
    }
    return res
}

async function search(text, reading="") {
    let res = searchReading(text, reading);
    res.length != 0 ? null : res = searchReading(text)
    res.length != 0 ? null : res = searchParticle(text)
    res.length != 0 ? null : res = searchVerb(text, reading)
    res.length != 0 ? null : res = searchKanji(text)
    return sort(res)
}

function createElement(tag, className="", id="", text="") {
    let e = document.createElement(tag)
    className ? e.className = className : null
    id ? e.id = id : null
    text ? e.innerText = text : null
    return e
}

function createConcept(entry) {
    let concept = createElement("div", "concept_light clearfix")
    let concept_wrapper = createElement("div", "concept_light-wrapper")
    let concept_readings = createElement("div", "concept_light-readings japanese_gothic")
    let concept_representation = createElement("div", "concept_light-representation")
    let furigana = createElement("span", "furigana")
    let kanji = createElement("span", "kanji", "", entry.r[0])
    let text = createElement("span", "text", "", (entry.k[0] ? entry.k[0] : entry.r[0]))

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

function createKanji(kanji) {
    let entry = createElement("div", "entry kanji_light clearfix")
    let content = createElement("div", "kanji_light_content")
    let literal_block = createElement("div", "literal_block")
    let character = createElement("div", "character literal japanese_gothic")
    character.appendChild(createElement("a", "", "", kanji))

    let meanings = createElement("div", "meanings english sense")
    meanings.appendChild(createElement("span", "", "", getMeanings(kanji).toString().replaceAll(",", ",  ")))

    let readings = createElement("div", "kun readings")
    readings.appendChild(createElement("span", "type", "", "Read: "))
    readings.appendChild(createElement("span", "japanese_gothic ", "", kanji.toString().replaceAll(",", ",  ")))

    literal_block.appendChild(character)
    content.appendChild(literal_block)
    content.appendChild(meanings)
    content.appendChild(createElement("div"))
    content.appendChild(readings)
    entry.appendChild(content)
    document.querySelector(".kanji_light_block").appendChild(entry)
}

function showDictionary(res) {
    let kanji = []
    console.log(res)
    document.getElementById("concepts_holder").innerHTML = ""
    document.querySelector(".kanji_light_block").innerHTML = ""
    res.forEach((entry) => {
        createConcept(entry)
        if (!entry.k[0])
            return
        getKanji(entry.k[0]).forEach((e) => {
            if (!kanji.includes(e)) {
                createKanji(e)
                kanji = kanji.concat(e)
            }
        })
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
        showDictionary(await search(target.innerText.replace(/[\p{White_Space}\p{Cf}]/gu, ""), sibling.innerText.replace(/[\p{White_Space}\p{Cf}]/gu, "")))
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