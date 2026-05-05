let chart = null;
const DEFAULT_TITLE = 'BTC Auto Trader';

function showDecisionPanel(prompt, price) {
  document.getElementById('decision-panel').classList.add('active');
  document.getElementById('decision-prompt').textContent = prompt;
  document.getElementById('decision-price').textContent = price ? `BTC ¥${Number(price).toLocaleString('ja-JP')}` : '';
  document.title = '⚡ 確認してください - ' + DEFAULT_TITLE;
}

function hideDecisionPanel() {
  document.getElementById('decision-panel').classList.remove('active');
  document.title = DEFAULT_TITLE;
}

async function submitDecision(action) {
  const reason = action === 'hold' ? 'ユーザーがHOLDを選択' : `ユーザーが${action.toUpperCase()}を選択`;
  ['btn-buy','btn-hold','btn-sell'].forEach(id => {
    document.getElementById(id).disabled = true;
  });
  try {
    await api.submitDecision(action, reason);
    // WebSocketが届かない場合のフォールバック
    hideDecisionPanel();
    updateLastTrade(action, reason, true);
    await new Promise(r => setTimeout(r, 1000));
    const [trades, history] = await Promise.all([api.getTrades(10), api.getAssetHistory(30)]);
    renderRecentTrades(trades.trades || []);
    initChart(history.history || []);
  } finally {
    ['btn-buy','btn-hold','btn-sell'].forEach(id => {
      document.getElementById(id).disabled = false;
    });
  }
}

function toJST(isoStr) {
  const s = isoStr.includes('+') || isoStr.endsWith('Z') ? isoStr : isoStr + 'Z';
  return new Date(s).toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo', hour12: false,
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).replace(/\//g, '/');
}

function fmt(n, decimals = 0) {
  return Number(n).toLocaleString('ja-JP', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtPrice(n) { return '¥' + fmt(n); }

function updateNav(status) {
  const dot = document.getElementById('status-dot');
  const label = document.getElementById('status-label');
  const btnStart = document.getElementById('btn-start');
  const btnStop = document.getElementById('btn-stop');
  const dryBadge = document.getElementById('dry-badge');

  if (status.is_running) {
    dot.className = 'status-dot running';
    label.textContent = '稼働中';
    btnStart.disabled = true;
    btnStop.disabled = false;
  } else {
    dot.className = 'status-dot stopped';
    label.textContent = '停止中';
    btnStart.disabled = false;
    btnStop.disabled = true;
  }

  if (status.is_dry_run !== undefined) {
    if (status.is_dry_run) {
      dryBadge.className = 'badge badge-dry';
      dryBadge.textContent = 'DRY RUN';
      dryBadge.dataset.mode = 'dry';
    } else {
      dryBadge.className = 'badge badge-live';
      dryBadge.textContent = 'LIVE';
      dryBadge.dataset.mode = 'live';
    }
  }
}

function updatePrice(data) {
  const last = parseFloat(data.last || 0);
  document.getElementById('price-last').textContent = fmtPrice(last);
  document.getElementById('price-high').textContent = fmtPrice(parseFloat(data.high || 0));
  document.getElementById('price-low').textContent = fmtPrice(parseFloat(data.low || 0));
  document.getElementById('price-vol').textContent = parseFloat(data.vol || 0).toFixed(2) + ' BTC';

  // BTC in JPY for balance card
  const btcValEl = document.getElementById('btc-jpy-val');
  if (btcValEl) {
    const btcBal = parseFloat(btcValEl.dataset.btc || 0);
    btcValEl.textContent = '≈ ' + fmtPrice(btcBal * last);
  }
}

function updateLastTrade(action, reason, isDry) {
  const el = document.getElementById('last-signal');
  if (!el) return;
  const flag = isDry ? ' [DRY]' : '';
  const badgeClass = action === 'buy' ? 'badge-buy' : action === 'sell' ? 'badge-sell' : 'badge-hold';
  el.innerHTML = `<span class="badge ${badgeClass}">${action.toUpperCase()}${flag}</span> ${reason || ''}`;
}

function renderRecentTrades(trades) {
  const tbody = document.getElementById('recent-trades');
  if (!tbody) return;
  tbody.innerHTML = '';
  trades.slice(0, 10).forEach(t => {
    const action = t.action;
    const flag = t.is_dry_run ? '<span class="badge badge-dry" style="font-size:10px">DRY</span>' : '';
    const badgeClass = action === 'buy' ? 'badge-buy' : action === 'sell' ? 'badge-sell' : 'badge-hold';
    const ts = toJST(t.timestamp);
    tbody.innerHTML += `
      <tr>
        <td>${ts}</td>
        <td><span class="badge ${badgeClass}">${action.toUpperCase()}</span> ${flag}</td>
        <td>${fmtPrice(t.price)}</td>
        <td>${fmtPrice(t.amount_jpy)}</td>
      </tr>`;
  });
  if (!trades.length) tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">取引履歴なし</td></tr>';
}

function initChart(history) {
  const ctx = document.getElementById('asset-chart');
  if (!ctx) return;

  const labels = history.map(h => h.timestamp.slice(5, 16).replace('T', ' '));
  const data = history.map(h => h.total_jpy);

  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '総資産 (JPY)',
        data,
        borderColor: '#f7931a',
        backgroundColor: 'rgba(247,147,26,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => '¥' + fmt(ctx.raw),
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#8b949e', maxTicksLimit: 6, font: { size: 11 } },
          grid: { color: 'rgba(48,54,61,0.5)' },
        },
        y: {
          ticks: {
            color: '#8b949e',
            font: { size: 11 },
            callback: v => '¥' + fmt(v),
          },
          grid: { color: 'rgba(48,54,61,0.5)' },
        }
      }
    }
  });
}

async function init() {
  let status = null;
  try {
    const [s, trades, history] = await Promise.all([
      api.getBotStatus(),
      api.getTrades(10),
      api.getAssetHistory(30),
    ]);
    status = s;

    updateNav(status);
    renderRecentTrades(trades.trades || []);
    initChart(history.history || []);

    if (status.last_action) {
      updateLastTrade(status.last_action, status.last_reason, status.is_dry_run);
    }
  } catch (e) {
    console.error('Init error:', e);
  }

  // Price WebSocket
  new ReconnectingWS('/ws/price', (data) => updatePrice(data));

  // 起動時に未応答のプロンプトがあれば復元
  if (status && status.has_pending && status.pending_prompt) {
    showDecisionPanel(status.pending_prompt, status.pending_price);
  }

  // Bot WebSocket
  new ReconnectingWS('/ws/bot', (data) => {
    if (data.event === 'status') updateNav(data);
    if (data.event === 'prompt_ready') {
      showDecisionPanel(data.prompt, data.price);
    }
    if (data.event === 'trade') {
      hideDecisionPanel();
      updateLastTrade(data.action, data.reason, data.is_dry_run);
      api.getTrades(10).then(r => renderRecentTrades(r.trades || []));
      api.getAssetHistory(30).then(r => initChart(r.history || []));
    }
  });

  document.getElementById('btn-start').addEventListener('click', async () => {
    updateNav({ is_running: true, is_dry_run: document.getElementById('dry-badge').dataset.mode === 'dry' });
    try { await api.startBot(); } catch (e) {
      updateNav({ is_running: false, is_dry_run: document.getElementById('dry-badge').dataset.mode === 'dry' });
    }
  });
  document.getElementById('btn-stop').addEventListener('click', async () => {
    updateNav({ is_running: false, is_dry_run: document.getElementById('dry-badge').dataset.mode === 'dry' });
    try { await api.stopBot(); } catch (e) {
      updateNav({ is_running: true, is_dry_run: document.getElementById('dry-badge').dataset.mode === 'dry' });
    }
  });

  document.getElementById('btn-trigger').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = '⏳ 実行中...';
    try {
      await api.triggerCycle();
      // WebSocketが届かない場合のポーリングフォールバック
      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const s = await api.getBotStatus();
        if (s.has_pending && s.pending_prompt) {
          showDecisionPanel(s.pending_prompt, s.pending_price);
          break;
        }
      }
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ テスト実行';
    }
  });

  document.getElementById('btn-copy-prompt').addEventListener('click', () => {
    const text = document.getElementById('decision-prompt').textContent;
    navigator.clipboard.writeText(text).then(() => {
      const btn = document.getElementById('btn-copy-prompt');
      btn.textContent = '✅ コピー完了';
      setTimeout(() => { btn.textContent = '📋 プロンプトをコピー'; }, 2000);
    });
  });

  document.getElementById('btn-buy').addEventListener('click',  () => submitDecision('buy'));
  document.getElementById('btn-hold').addEventListener('click', () => submitDecision('hold'));
  document.getElementById('btn-sell').addEventListener('click', () => submitDecision('sell'));
}

init();
