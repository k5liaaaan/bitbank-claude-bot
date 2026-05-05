function showAlert(msg, type = 'success') {
  const el = document.getElementById('alert-area');
  el.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
  setTimeout(() => { el.innerHTML = ''; }, 4000);
}

async function loadSettings() {
  try {
    const s = await api.getSettings();
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
    const setChk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = val === 'true' || val === true; };

    set('bitbank-key', s.bitbank_api_key || '');
    set('bitbank-secret', s.bitbank_api_secret || '');
    set('anthropic-key', s.anthropic_api_key || '');
    set('order-amount', s.order_amount_jpy || '10000');
    set('polling-interval', s.polling_interval_minutes || '15');
    const modeEl = document.getElementById('trading-mode');
    if (modeEl) modeEl.value = s.trading_mode || 'manual';
    set('global-stop-base', s.global_stop_base_asset_jpy || '100000');
    set('global-stop-pct', s.global_stop_loss_pct || '20');
    setChk('dry-run', s.dry_run);
    setChk('global-stop-enabled', s.global_stop_enabled);

    set('slack-bot-token', s.slack_bot_token || '');
    set('slack-app-token', s.slack_app_token || '');
    set('slack-channel', s.slack_channel || '');

    const statusEl = document.getElementById('slack-status');
    if (statusEl) {
      const hasCreds = s.slack_bot_token && s.slack_app_token && s.slack_channel;
      statusEl.innerHTML = hasCreds
        ? '<span style="color:var(--up)">● 設定済み（再起動後に接続）</span>'
        : '<span style="color:var(--text-muted)">○ 未設定</span>';
    }

    updateStopCalc();
  } catch (e) {
    showAlert('設定の読み込みに失敗しました', 'error');
  }
}

async function loadRules() {
  try {
    const data = await api.getRules();
    document.getElementById('rules-editor').value = data.content || '';
  } catch (e) {
    showAlert('ルールの読み込みに失敗しました', 'error');
  }
}

function updateStopCalc() {
  const base = parseFloat(document.getElementById('global-stop-base')?.value || 0);
  const pct = parseFloat(document.getElementById('global-stop-pct')?.value || 0);
  const threshold = base * (1 - pct / 100);
  const el = document.getElementById('stop-calc');
  if (el && base > 0) {
    el.textContent = `→ 残高が ¥${threshold.toLocaleString('ja-JP', {maximumFractionDigits: 0})} を下回ると自動停止`;
  }
}

document.getElementById('global-stop-base')?.addEventListener('input', updateStopCalc);
document.getElementById('global-stop-pct')?.addEventListener('input', updateStopCalc);

document.getElementById('form-api')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = {};
  const key = document.getElementById('bitbank-key').value;
  const secret = document.getElementById('bitbank-secret').value;
  const antKey = document.getElementById('anthropic-key').value;
  if (key && !key.startsWith('••••')) data.bitbank_api_key = key;
  if (secret && !secret.startsWith('••••')) data.bitbank_api_secret = secret;
  if (antKey && !antKey.startsWith('••••')) data.anthropic_api_key = antKey;
  try {
    await api.updateSettings(data);
    showAlert('APIキーを保存しました');
    loadSettings();
  } catch { showAlert('保存に失敗しました', 'error'); }
});

document.getElementById('form-trading')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = {
    dry_run: document.getElementById('dry-run').checked,
    order_amount_jpy: parseFloat(document.getElementById('order-amount').value),
    polling_interval_minutes: parseInt(document.getElementById('polling-interval').value),
    trading_mode: document.getElementById('trading-mode').value,
  };
  try {
    await api.updateSettings(data);
    showAlert('取引設定を保存しました');
    loadSettings();
  } catch { showAlert('保存に失敗しました', 'error'); }
});

document.getElementById('form-stop')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = {
    global_stop_enabled: document.getElementById('global-stop-enabled').checked,
    global_stop_base_asset_jpy: parseFloat(document.getElementById('global-stop-base').value),
    global_stop_loss_pct: parseFloat(document.getElementById('global-stop-pct').value),
  };
  try {
    await api.updateSettings(data);
    showAlert('グローバルストップを保存しました');
    updateStopCalc();
  } catch { showAlert('保存に失敗しました', 'error'); }
});

document.getElementById('form-rules')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const content = document.getElementById('rules-editor').value;
  try {
    await api.updateRules(content);
    showAlert('取引ルールを保存しました');
  } catch { showAlert('保存に失敗しました', 'error'); }
});

document.getElementById('form-slack')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = {};
  const botToken = document.getElementById('slack-bot-token').value;
  const appToken = document.getElementById('slack-app-token').value;
  const channel = document.getElementById('slack-channel').value;
  if (botToken && !botToken.startsWith('••••')) data.slack_bot_token = botToken;
  if (appToken && !appToken.startsWith('••••')) data.slack_app_token = appToken;
  if (channel) data.slack_channel = channel;
  try {
    await api.updateSettings(data);
    showAlert('Slack設定を保存しました。Dockerを再起動すると接続します。');
    loadSettings();
  } catch { showAlert('保存に失敗しました', 'error'); }
});

loadSettings();
loadRules();
