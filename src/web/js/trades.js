let offset = 0;
const LIMIT = 100;
let allTrades = [];

function toJST(isoStr) {
  const s = isoStr.includes('+') || isoStr.endsWith('Z') ? isoStr : isoStr + 'Z';
  return new Date(s).toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo', hour12: false,
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).replace(/\//g, '/');
}

function fmt(n, d = 0) {
  return Number(n).toLocaleString('ja-JP', { minimumFractionDigits: d, maximumFractionDigits: d });
}

function renderTrades(trades) {
  const tbody = document.getElementById('trades-body');
  tbody.innerHTML = '';
  if (!trades.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:32px">取引履歴なし</td></tr>';
    return;
  }
  trades.forEach(t => {
    const action = t.action;
    const badgeClass = action === 'buy' ? 'badge-buy' : action === 'sell' ? 'badge-sell' : 'badge-hold';
    const dryFlag = t.is_dry_run ? '<span class="badge badge-dry" style="font-size:10px;margin-left:4px">DRY</span>' : '';
    const ts = toJST(t.timestamp);
    tbody.innerHTML += `
      <tr>
        <td style="color:var(--text-muted)">${ts}</td>
        <td><span class="badge ${badgeClass}">${action.toUpperCase()}</span>${dryFlag}</td>
        <td>¥${fmt(t.price)}</td>
        <td>${parseFloat(t.amount_btc).toFixed(6)} BTC</td>
        <td>¥${fmt(t.amount_jpy)}</td>
        <td style="color:var(--text-muted);font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.reason || '-'}</td>
        <td style="color:var(--text-muted);font-size:11px">${t.order_id || '-'}</td>
      </tr>`;
  });
}

function exportCSV() {
  const header = ['timestamp', 'action', 'price', 'amount_btc', 'amount_jpy', 'reason', 'is_dry_run', 'order_id'];
  const rows = allTrades.map(t =>
    header.map(k => JSON.stringify(t[k] ?? '')).join(',')
  );
  const csv = [header.join(','), ...rows].join('\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}

async function load() {
  try {
    const data = await api.getTrades(LIMIT, offset);
    allTrades = data.trades || [];
    renderTrades(allTrades);
    document.getElementById('page-info').textContent =
      `${offset + 1}〜${offset + allTrades.length} 件`;
    document.getElementById('btn-prev').disabled = offset === 0;
    document.getElementById('btn-next').disabled = allTrades.length < LIMIT;
  } catch (e) {
    console.error(e);
  }
}

document.getElementById('btn-prev').addEventListener('click', () => {
  if (offset >= LIMIT) { offset -= LIMIT; load(); }
});
document.getElementById('btn-next').addEventListener('click', () => {
  offset += LIMIT; load();
});
document.getElementById('btn-export').addEventListener('click', exportCSV);

load();
