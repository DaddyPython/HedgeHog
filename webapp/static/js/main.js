const symbolSelect = document.getElementById('symbolSelect');
const executeBtn = document.getElementById('executeBtn');
const stopBtn = document.getElementById('stopBtn');
const tpSlider = document.getElementById('tpSlider');
const slSlider = document.getElementById('slSlider');
const tpValue = document.getElementById('tpValue');
const slValue = document.getElementById('slValue');
const sizeInput = document.getElementById('sizeInput');
const logStream = document.getElementById('logStream');

const LEVEL_CLASS = {
  info: 'success',
  warning: 'warning',
  error: 'error',
};

function appendLog(level, message) {
  const entry = document.createElement('div');
  entry.className = `log-entry ${LEVEL_CLASS[level] || 'success'}`;
  entry.textContent = message;
  logStream.appendChild(entry);
  logStream.scrollTop = logStream.scrollHeight;
}

async function loadSymbols() {
  try {
    const response = await fetch('/api/symbols');
    const data = await response.json();
    if (data.error) {
      appendLog('error', `Symbol fetch error: ${data.error}`);
      return;
    }
    symbolSelect.innerHTML = '';
    data.symbols.forEach((symbol) => {
      const option = document.createElement('option');
      option.value = symbol;
      option.textContent = symbol;
      symbolSelect.appendChild(option);
    });
    appendLog('info', `Loaded ${data.symbols.length} symbols.`);
  } catch (error) {
    appendLog('error', `Failed to load symbols: ${error}`);
  }
}

async function executeTrade() {
  const payload = {
    symbol: symbolSelect.value,
    size: Number(sizeInput.value || 1),
    takeProfit: Number(tpSlider.value) / 100,
    stopLoss: Number(slSlider.value) / 100,
  };
  try {
    appendLog('info', `Executing dual orders for ${payload.symbol}`);
    const response = await fetch('/api/execute', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unknown error');
    }
    appendLog('info', `Orders placed: Long ${data.long?.order_id} / Short ${data.short?.order_id}`);
  } catch (error) {
    appendLog('error', `Execute failed: ${error}`);
  }
}

async function stopAll() {
  try {
    const symbol = symbolSelect.value;
    appendLog('warning', `Cancelling all for ${symbol}`);
    const response = await fetch('/api/cancel', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ symbol }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Unknown error');
    }
    appendLog('info', `Cancel confirmation: ${JSON.stringify(data)}`);
  } catch (error) {
    appendLog('error', `Cancel failed: ${error}`);
  }
}

function attachEvents() {
  tpSlider.addEventListener('input', () => {
    tpValue.textContent = `${tpSlider.value}%`;
  });
  slSlider.addEventListener('input', () => {
    slValue.textContent = `${slSlider.value}%`;
  });
  executeBtn.addEventListener('click', executeTrade);
  stopBtn.addEventListener('click', stopAll);
}

function initLogStream() {
  const eventSource = new EventSource('/logs');
  eventSource.addEventListener('log', (event) => {
    try {
      const data = JSON.parse(event.data);
      appendLog(data.level, data.message);
    } catch (error) {
      appendLog('error', `Log parse error: ${error}`);
    }
  });
  eventSource.onerror = () => {
    appendLog('error', 'Log stream disconnected. Retrying...');
  };
}

loadSymbols();
setInterval(loadSymbols, 15000);
attachEvents();
initLogStream();
