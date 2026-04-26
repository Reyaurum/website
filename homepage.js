const TOTAL_CHAPTERS = 27;
const PAGE_SIZE = 20;
const CHAPTER_TITLES = {};

function getTitle(n) { return CHAPTER_TITLES[n] || null }
function chapterHref(n) { return `/website/ch-${n}/` }
function getLastRead() { try { return parseInt(localStorage.getItem("lrc") || "0", 10) } catch { return 0 } }
function setLastRead(n) { try { localStorage.setItem("lrc", n) } catch { } }

let lastRead = getLastRead();
let filteredChapters = [];
let currentPage = 0;

function buildAll() {
    filteredChapters = [];
    for (let i = 1; i <= TOTAL_CHAPTERS; i++) filteredChapters.push(i);
}

function applySearch(q) {
    q = q.trim().toLowerCase();
    if (!q) { buildAll(); return }
    const num = parseInt(q, 10);
    filteredChapters = [];
    for (let i = 1; i <= TOTAL_CHAPTERS; i++) {
        const t = getTitle(i);
        const numMatch = !isNaN(num) && i === num;
        const titleMatch = t && t.toLowerCase().includes(q);
        const numStrMatch = String(i).includes(q);
        if (numMatch || titleMatch || numStrMatch) filteredChapters.push(i);
    }
}

function highlight(text, q) {
    if (!q) return text;
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    if (idx < 0) return text;
    return text.slice(0, idx) + '<em>' + text.slice(idx, idx + q.length) + '</em>' + text.slice(idx + q.length);
}

function renderPage() {
    const q = document.getElementById("searchInput").value.trim().toLowerCase();
    const total = filteredChapters.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage >= totalPages) currentPage = totalPages - 1;
    const start = currentPage * PAGE_SIZE;
    const slice = filteredChapters.slice(start, start + PAGE_SIZE);

    document.getElementById("resultCount").textContent =
        q ? `${total.toLocaleString()} result${total !== 1 ? 's' : ''}` :
            `${total.toLocaleString()} chapters`;

    const container = document.getElementById("listContainer");
    if (slice.length === 0) {
        container.innerHTML = '<div class="empty">No chapters found.</div>';
        document.getElementById("paginationBar").innerHTML = '';
        return;
    }

    let html = '<div class="ch-list">';
    for (const n of slice) {
        const rawTitle = getTitle(n);
        const titleStr = rawTitle ? highlight(rawTitle, q) : '';
        const numStr = q ? highlight(String(n), q) : String(n);
        html += `<a class="ch-row" href="${chapterHref(n)}" data-n="${n}">
      <span class="ch-num-col">Ch. ${numStr}</span>
      <span class="ch-divider"></span>
      <span class="ch-title-col">${titleStr || '<span style="color:var(--muted);font-style:italic">Untitled</span>'}</span>
      <span class="ch-arrow">→</span>
    </a>`;
    }
    html += '</div>';
    container.innerHTML = html;

    container.querySelectorAll('.ch-row').forEach(el => {
        el.addEventListener('click', e => {
            e.preventDefault();
            const n = parseInt(el.dataset.n, 10);
            setLastRead(n);
            window.location.href = chapterHref(n);
        });
    });

    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    const bar = document.getElementById("paginationBar");
    if (totalPages <= 1) { bar.innerHTML = ''; return }

    const start = currentPage * PAGE_SIZE + 1;
    const end = Math.min(start + PAGE_SIZE - 1, filteredChapters.length);
    let html = `<span class="page-info">Showing ${start.toLocaleString()}–${end.toLocaleString()} of ${filteredChapters.length.toLocaleString()}</span>`;
    html += '<div class="page-btns">';
    html += `<button class="page-btn nav" onclick="goPage(${currentPage - 1})" ${currentPage === 0 ? 'disabled style="opacity:.3;cursor:default"' : ''}>← Prev</button>`;

    const windowSize = 3;
    let pStart = Math.max(0, currentPage - Math.floor(windowSize / 2));
    let pEnd = Math.min(totalPages - 1, pStart + windowSize - 1);
    if (pEnd - pStart < windowSize - 1) pStart = Math.max(0, pEnd - windowSize + 1);

    if (pStart > 0) {
        html += `<button class="page-btn" onclick="goPage(0)">1</button>`;
        if (pStart > 1) html += `<button class="page-btn" style="pointer-events:none;opacity:.4">…</button>`;
    }
    for (let p = pStart; p <= pEnd; p++) {
        html += `<button class="page-btn${p === currentPage ? ' active' : ''}" onclick="goPage(${p})">${p + 1}</button>`;
    }
    if (pEnd < totalPages - 1) {
        if (pEnd < totalPages - 2) html += `<button class="page-btn" style="pointer-events:none;opacity:.4">…</button>`;
        html += `<button class="page-btn" onclick="goPage(${totalPages - 1})">${totalPages}</button>`;
    }
    html += `<button class="page-btn nav" onclick="goPage(${currentPage + 1})" ${currentPage === totalPages - 1 ? 'disabled style="opacity:.3;cursor:default"' : ''}>Next →</button>`;
    html += '</div>';
    bar.innerHTML = html;
}

function goPage(p) {
    const totalPages = Math.ceil(filteredChapters.length / PAGE_SIZE);
    if (p < 0 || p >= totalPages) return;
    currentPage = p;
    renderPage();
    document.querySelector('.section-head').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function jumpTo() {
    const val = parseInt(document.getElementById("searchInput").value, 10);
    if (isNaN(val) || val < 1 || val > TOTAL_CHAPTERS) return;
    document.getElementById("searchInput").value = '';
    buildAll();
    currentPage = Math.floor((val - 1) / PAGE_SIZE);
    renderPage();
    setTimeout(() => {
        const el = document.querySelector(`.ch-row[data-n="${val}"]`);
        if (el) { el.style.background = 'rgba(200,144,58,0.12)'; el.scrollIntoView({ behavior: 'smooth', block: 'center' }); setTimeout(() => { el.style.background = '' }, 1200); }
    }, 80);
}

document.addEventListener("DOMContentLoaded", () => {
    buildAll();
    renderPage();

    document.getElementById("searchInput").addEventListener("input", () => {
        const q = document.getElementById("searchInput").value;
        applySearch(q);
        currentPage = 0;
        renderPage();
    });
    document.getElementById("searchInput").addEventListener("keydown", e => { if (e.key === "Enter") jumpTo(); });

    document.getElementById("totalDisplay").textContent = TOTAL_CHAPTERS.toLocaleString();
    document.getElementById("readDisplay").textContent = lastRead.toLocaleString();
    document.getElementById("pctDisplay").textContent = Math.floor(lastRead / TOTAL_CHAPTERS * 100) + '%';

    if (lastRead > 0 && lastRead <= TOTAL_CHAPTERS) {
        const next = Math.min(lastRead, TOTAL_CHAPTERS);
        const t = getTitle(next);
        const pct = Math.floor(lastRead / TOTAL_CHAPTERS * 100);
        const band = document.getElementById("continueBand");
        document.getElementById("cbTitle").textContent = `Chapter ${next}${t ? ' — ' + t : ''}`;
        document.getElementById("cbBar").style.width = pct + '%';
        document.getElementById("cbPct").textContent = pct + '% complete';
        band.style.display = 'flex';
        band.onclick = () => { setLastRead(next); window.location.href = chapterHref(next); };
    }
});
