function toJST(isoStr) {
  const s = isoStr.includes('+') || isoStr.endsWith('Z') ? isoStr : isoStr + 'Z';
  return new Date(s).toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo', hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).replace(/\//g, '-');
}

let autoScroll = true;
const stream = document.getElementById('log-stream');
const levelFilter = document.getElementById('level-filter');

function appendLog(entry) {
  const selected = levelFilter.value;
  if (selected !== 'ALL' && entry.level !== selected) return;

  const ts = toJST(entry.timestamp);
  const line = document.createElement('div');
  line.className = 'log-line';
  line.dataset.level = entry.level;
  line.innerHTML =
    `<span class="log-ts">${ts}</span>` +
    `<span class="log-level ${entry.level}">${entry.level.padEnd(7)}</span>` +
    `<span class="log-msg">${entry.message}</span>`;
  stream.appendChild(line);

  if (autoScroll) stream.scrollTop = stream.scrollHeight;
}

function applyFilter() {
  const selected = levelFilter.value;
  stream.querySelectorAll('.log-line').forEach(el => {
    el.style.display = (selected === 'ALL' || el.dataset.level === selected) ? '' : 'none';
  });
}

async function loadInitial() {
  try {
    const data = await api.getLogs(200);
    const logs = (data.logs || []).reverse();
    stream.innerHTML = '';
    logs.forEach(appendLog);
  } catch (e) {
    console.error(e);
  }
}

levelFilter.addEventListener('change', applyFilter);

document.getElementById('btn-clear').addEventListener('click', () => {
  stream.innerHTML = '';
});

document.getElementById('btn-scroll').addEventListener('click', () => {
  autoScroll = !autoScroll;
  const btn = document.getElementById('btn-scroll');
  btn.textContent = autoScroll ? '自動スクロール: ON' : '自動スクロール: OFF';
  btn.style.color = autoScroll ? 'var(--up)' : 'var(--text-muted)';
});

stream.addEventListener('scroll', () => {
  const atBottom = stream.scrollHeight - stream.scrollTop <= stream.clientHeight + 20;
  if (!atBottom) autoScroll = false;
});

new ReconnectingWS('/ws/logs', appendLog);

loadInitial();
