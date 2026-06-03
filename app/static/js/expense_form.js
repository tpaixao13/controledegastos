document.addEventListener('DOMContentLoaded', function () {
  const paymentSelect      = document.getElementById('payment_method');
  const bankRow            = document.getElementById('bank-row');
  const bankSelect         = bankRow ? bankRow.querySelector('select') : null;
  const cardRow            = document.getElementById('card-row');
  const cardSelect         = document.getElementById('card_id');
  const billingHint        = document.getElementById('billing-hint');
  const installmentSection = document.getElementById('installment-section');
  const numInstallmentsRow = document.getElementById('num-installments-row');
  const creditTypeRadios   = document.querySelectorAll('input[name="credit_type"]');
  const recurringCheck     = document.getElementById('is_recurring');
  const recurringTimesRow  = document.getElementById('recurring-times-row');
  const dayInput           = document.querySelector('input[name="day"]');
  const monthSelect        = document.querySelector('select[name="month"]');
  const yearInput          = document.querySelector('input[name="year"]');
  const amountInput        = document.querySelector('input[name="amount"]');

  // Dados dos cartões injetados pelo template
  const cardData = window._cardData || {};

  const MONTH_NAMES = [
    'Janeiro','Fevereiro','Março','Abril','Maio','Junho',
    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro',
  ];

  const _CARD_FILTER = {
    'Cartão de Crédito': c => c.supports_credit === true,
    'Cartão de Débito':  c => c.supports_debit  === true,
    'VR':                c => c.card_type === 'vr',
    'VA':                c => c.card_type === 'va',
  };

  function filterCardOptions(method, selectedBank) {
    if (!cardSelect) return;
    const fn = _CARD_FILTER[method] || (() => false);
    const visible = [];
    Array.from(cardSelect.options).forEach(opt => {
      if (opt.value === '0') { opt.style.display = ''; return; }
      const card = cardData[parseInt(opt.value)];
      const matchMethod = card && fn(card);
      const matchBank   = !selectedBank || card.bank === selectedBank;
      const show = matchMethod && matchBank;
      opt.style.display = show ? '' : 'none';
      if (show) visible.push(opt.value);
    });
    const v = parseInt(cardSelect.value, 10);
    if (v > 0) {
      const card = cardData[v];
      if (!card || !fn(card) || (selectedBank && card.bank !== selectedBank)) {
        cardSelect.value = '0';
      }
    }
    // Auto-selecionar se só existe um cartão compatível
    if (visible.length === 1 && parseInt(cardSelect.value, 10) === 0) {
      cardSelect.value = visible[0];
    }
  }

  // ── Visibilidade dos campos ────────────────────────────────────
  function updateForm() {
    const method       = paymentSelect ? paymentSelect.value : '';
    const isCredit     = method === 'Cartão de Crédito';
    const hasBank      = ['PIX', 'Cartão de Débito', 'Cartão de Crédito', 'VR', 'VA'].includes(method);
    const isCardMethod = !!_CARD_FILTER[method];
    const selectedBank = bankSelect ? bankSelect.value : '';

    if (bankRow)            bankRow.style.display = hasBank ? '' : 'none';
    if (installmentSection) installmentSection.style.display = isCredit ? '' : 'none';
    if (numInstallmentsRow && !isCredit) numInstallmentsRow.style.display = 'none';
    if (!isCredit && billingHint)        billingHint.style.display = 'none';

    // Cartão só aparece depois que o banco for selecionado
    if (isCardMethod && selectedBank) {
      filterCardOptions(method, selectedBank);
      if (cardRow) cardRow.style.display = '';
    } else {
      if (cardRow) cardRow.style.display = 'none';
      if (cardSelect) cardSelect.value = '0';
    }

    if (isCredit) {
      updateInstallments();
      updateBillingHint();
    }
  }

  function updateInstallments() {
    const checked = document.querySelector('input[name="credit_type"]:checked');
    if (numInstallmentsRow)
      numInstallmentsRow.style.display = (checked?.value === 'parcelado') ? '' : 'none';
  }

  function updateRecurring() {
    if (!recurringTimesRow) return;
    recurringTimesRow.style.display = (recurringCheck?.checked) ? '' : 'none';
  }

  // ── Invoice Preview ────────────────────────────────────────────
  let _hintTimer = null;

  function _fmtBrl(v) {
    return 'R$ ' + v.toFixed(2)
      .replace('.', ',')
      .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function updateBillingHint() {
    if (!billingHint || !cardSelect || !dayInput || !monthSelect) {
      if (billingHint) billingHint.style.display = 'none';
      return;
    }

    const cardId = parseInt(cardSelect.value, 10);
    const card   = cardData[cardId];
    const day    = parseInt(dayInput.value, 10);
    const month  = parseInt(monthSelect.value, 10);
    const year   = parseInt(yearInput?.value, 10) || new Date().getFullYear();
    const amount = parseFloat(amountInput?.value) || 0;

    if (!card || !cardId || !day || !month) {
      billingHint.style.display = 'none';
      return;
    }

    // Calcular fatura localmente (instantâneo)
    const isOpen = day <= card.best_buy_day;
    let invMonth = month, invYear = year;
    if (!isOpen) {
      if (month === 12) { invMonth = 1; invYear = year + 1; }
      else              { invMonth = month + 1; }
    }

    const invoiceLabel  = MONTH_NAMES[invMonth - 1] + ' ' + invYear;
    const daysToClosing = isOpen ? card.best_buy_day - day : null;
    const closingTxt    = daysToClosing !== null
      ? ` · fecha em ${daysToClosing} dia${daysToClosing !== 1 ? 's' : ''}`
      : '';

    if (isOpen) {
      billingHint.innerHTML = `
        <div class="d-flex align-items-start gap-2 p-2 rounded border border-success bg-success bg-opacity-10">
          <i class="bi bi-check-circle-fill text-success fs-5 flex-shrink-0" style="margin-top:2px"></i>
          <div class="flex-grow-1">
            <div class="fw-semibold small">
              <span class="text-success">&#x2705; Vai cair na fatura de <strong>${invoiceLabel}</strong></span>
            </div>
            <div class="text-muted" style="font-size:.78rem">Vence dia ${card.due_day}${closingTxt}</div>
            <div class="hint-limit" style="display:none">
              <div class="progress mt-2" style="height:5px;border-radius:3px">
                <div class="hint-bar progress-bar bg-success" style="width:0%;transition:width .5s ease"></div>
              </div>
              <div class="hint-limit-text text-muted mt-1" style="font-size:.78rem"></div>
            </div>
          </div>
        </div>`;
    } else {
      billingHint.innerHTML = `
        <div class="d-flex align-items-start gap-2 p-2 rounded border border-warning bg-warning bg-opacity-10">
          <i class="bi bi-arrow-right-circle-fill text-warning fs-5 flex-shrink-0" style="margin-top:2px"></i>
          <div class="flex-grow-1">
            <div class="fw-semibold small">
              <span class="text-warning">&#x26A0;&#xFE0F; Entra na fatura de <strong>${invoiceLabel}</strong></span>
            </div>
            <div class="text-muted" style="font-size:.78rem">Fatura atual j&aacute; fechou &middot; pr&oacute;xima vence dia ${card.due_day}</div>
            <div class="hint-limit" style="display:none">
              <div class="progress mt-2" style="height:5px;border-radius:3px">
                <div class="hint-bar progress-bar bg-success" style="width:0%;transition:width .5s ease"></div>
              </div>
              <div class="hint-limit-text text-muted mt-1" style="font-size:.78rem"></div>
            </div>
          </div>
        </div>`;
    }
    billingHint.style.display = '';

    // Busca limite no servidor (debounced)
    clearTimeout(_hintTimer);
    _hintTimer = setTimeout(async () => {
      if (!card.credit_limit) return;
      try {
        const p = new URLSearchParams({ card_id: cardId, day, month, year, amount });
        const res = await fetch('/cards/api/invoice-preview?' + p);
        if (!res.ok) return;
        const srv = await res.json();
        const usage = srv.projected_usage ?? srv.current_usage;
        if (usage !== null && usage !== undefined && card.credit_limit) {
          const pct    = Math.min(usage / card.credit_limit * 100, 100);
          const bColor = pct > 80 ? 'bg-danger' : pct > 60 ? 'bg-warning' : 'bg-success';
          const lDiv   = billingHint.querySelector('.hint-limit');
          const bar    = billingHint.querySelector('.hint-bar');
          const ltxt   = billingHint.querySelector('.hint-limit-text');
          if (lDiv && bar && ltxt) {
            bar.style.width = pct + '%';
            bar.className   = 'hint-bar progress-bar ' + bColor;
            ltxt.innerHTML  = `Ap&oacute;s essa compra: <strong>${_fmtBrl(usage)}</strong> / ${_fmtBrl(card.credit_limit)} (${pct.toFixed(0)}%)`;
            lDiv.style.display = '';
          }
        }
      } catch (_) {}
    }, 350);
  }

  // ── Listeners ──────────────────────────────────────────────────
  if (paymentSelect) paymentSelect.addEventListener('change', updateForm);
  if (bankSelect)    bankSelect.addEventListener('change', updateForm);
  creditTypeRadios.forEach(r => r.addEventListener('change', updateInstallments));
  if (recurringCheck) recurringCheck.addEventListener('change', updateRecurring);
  if (cardSelect) cardSelect.addEventListener('change', updateBillingHint);
  if (dayInput)   dayInput.addEventListener('input', updateBillingHint);
  if (monthSelect) monthSelect.addEventListener('change', updateBillingHint);
  if (yearInput)  yearInput.addEventListener('change', updateBillingHint);
  if (amountInput) amountInput.addEventListener('input', () => {
    clearTimeout(_hintTimer);
    _hintTimer = setTimeout(updateBillingHint, 350);
  });

  // ── Sugestão automática de categoria ──────────────────────────
  const descInput     = document.getElementById('description');
  const categoryInput = document.getElementById('category');
  let _suggestTimer   = null;

  if (descInput) {
    descInput.addEventListener('input', function () {
      clearTimeout(_suggestTimer);
      _suggestTimer = setTimeout(() => {
        if (!categoryInput || categoryInput.value.trim()) return;
        const desc = descInput.value.trim();
        if (desc.length < 3) return;
        fetch('/api/chart/suggest-category?description=' + encodeURIComponent(desc))
          .then(r => r.json())
          .then(d => { if (d.category && !categoryInput.value.trim()) categoryInput.value = d.category; })
          .catch(() => {});
      }, 400);
    });
  }

  // ── Inicialização ──────────────────────────────────────────────
  updateForm();
  updateRecurring();
});
