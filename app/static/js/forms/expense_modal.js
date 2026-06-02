/**
 * FinFam — Expense Modal
 * Modal de cadastro de despesa com UX progressivo e submit via AJAX.
 */

(() => {
  const MONTH_NAMES = [
    'Janeiro','Fevereiro','Março','Abril','Maio','Junho',
    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro',
  ];

  // ── Elementos ──────────────────────────────────────────────────
  const modalEl   = document.getElementById('expenseModal');
  const form      = document.getElementById('expenseModalForm');
  const saveBtn   = document.getElementById('btnSaveExpense');
  const errorAlert = document.getElementById('modalErrorAlert');
  const errorMsg   = document.getElementById('modalErrorMsg');

  if (!modalEl || !form) return;

  // Essenciais
  const fPayment     = form.querySelector('#m_payment_method');
  const fDescription = form.querySelector('#m_description');
  const fCategory    = form.querySelector('#m_category');
  const fDay         = form.querySelector('#m_day');
  const fMonth       = form.querySelector('#m_month');
  const fYear        = form.querySelector('#m_year');
  const fAmount      = form.querySelector('#m_amount');

  // Avançados
  const bankRow         = form.querySelector('#m_bank_row');
  const cardRow         = form.querySelector('#m_card_row');
  const cardSelect      = form.querySelector('#m_card_id');
  const creditTypeRow   = form.querySelector('#m_credit_type_row');
  const installmentsRow = form.querySelector('#m_installments_row');
  const recurringCheck  = form.querySelector('#m_is_recurring');
  const recurringRow    = form.querySelector('#m_recurring_times_row');
  const toggleBtn       = form.querySelector('#btnToggleAdvanced');
  const advSection      = form.querySelector('#advancedSection');
  const toggleLabel     = form.querySelector('#toggleAdvancedLabel');

  // Mapa de dados dos cartões injetado pelo backend
  const cardData = window._modalCardData || {};

  // ── Estado da seção avançada ────────────────────────────────────
  let advancedOpen = false;

  function openAdvanced() {
    advancedOpen = true;
    advSection.classList.add('open');
    if (toggleLabel) toggleLabel.textContent = '− Ocultar opções avançadas';
  }
  function closeAdvanced() {
    advancedOpen = false;
    advSection.classList.remove('open');
    if (toggleLabel) toggleLabel.textContent = '+ Opções avançadas';
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      advancedOpen ? closeAdvanced() : openAdvanced();
    });
  }

  // ── Lógica condicional de campos ───────────────────────────────
  const _BANK_METHODS  = ['PIX', 'Cartão de Débito', 'Cartão de Crédito', 'VR', 'VA'];
  const _METHOD_TO_TYPE = {
    'Cartão de Crédito': 'credit',
    'Cartão de Débito':  'debit',
    'VR': 'vr',
    'VA': 'va',
  };

  function updateCardOptions(method) {
    if (!cardSelect) return;
    const targetType = _METHOD_TO_TYPE[method];
    Array.from(cardSelect.options).forEach(opt => {
      if (opt.value === '0') { opt.style.display = ''; return; }
      const optType = opt.dataset.type || 'credit';
      opt.style.display = (targetType && optType === targetType) ? '' : 'none';
    });
    const selVal = parseInt(cardSelect.value, 10);
    if (selVal > 0) {
      const selOpt = cardSelect.querySelector(`option[value="${selVal}"]`);
      if (selOpt && selOpt.style.display === 'none') cardSelect.value = '0';
    }
  }

  function autofillBankFromCard() {
    const id = parseInt(cardSelect?.value, 10);
    const card = cardData[id];
    if (!card || !id) return;
    const bankSel = form.querySelector('#m_bank');
    if (bankSel && card.bank) bankSel.value = card.bank;
  }

  function updateInstallmentHint() {
    const hintRow = form.querySelector('#m_installment_hint');
    const preview = form.querySelector('#m_installment_preview');
    const isCredit    = fPayment?.value === 'Cartão de Crédito';
    const isParcelado = form.querySelector('#m_credit_parcelado')?.checked;
    if (!isCredit || !isParcelado) {
      hintRow?.classList.add('d-none');
      return;
    }
    hintRow?.classList.remove('d-none');
    const amount = parseFloat(fAmount?.value) || 0;
    const num    = parseInt(form.querySelector('#m_num_installments')?.value) || 1;
    if (preview) {
      preview.textContent = (amount > 0 && num > 1)
        ? `Cada parcela: ${_fmtBrl(amount / num)}`
        : '';
    }
  }

  function updateFields() {
    const method       = fPayment?.value || '';
    const isCredit     = method === 'Cartão de Crédito';
    const hasBank      = _BANK_METHODS.includes(method);
    const isCardMethod = !!_METHOD_TO_TYPE[method];
    const isParcelado  = form.querySelector('#m_credit_parcelado')?.checked;

    bankRow?.classList.toggle('d-none', !hasBank);
    creditTypeRow?.classList.toggle('d-none', !isCredit);
    installmentsRow?.classList.toggle('d-none', !(isCredit && isParcelado));

    if (isCardMethod) {
      updateCardOptions(method);
      cardRow?.classList.remove('d-none');
    } else {
      cardRow?.classList.add('d-none');
    }

    updateInstallmentHint();
    updateInvoicePreview();
  }

  // ── Invoice Preview ────────────────────────────────────────────
  let _invoiceTimer = null;

  function _fmtBrl(v) {
    return 'R$ ' + v.toFixed(2)
      .replace('.', ',')
      .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function _computeInvoice(cardId, day, month, year) {
    const card = cardData[parseInt(cardId, 10)];
    if (!card || !day || !month || !year) return null;

    const isOpen = day <= card.best_buy_day;
    let invMonth = month;
    let invYear  = year;

    if (!isOpen) {
      if (month === 12) { invMonth = 1; invYear = year + 1; }
      else              { invMonth = month + 1; }
    }

    return {
      isOpen,
      invMonth,
      invYear,
      invoiceLabel:   MONTH_NAMES[invMonth - 1] + ' ' + invYear,
      daysToClosing:  isOpen ? card.best_buy_day - day : null,
      dueDay:         card.due_day,
      creditLimit:    card.credit_limit || null,
    };
  }

  function _renderInvoice(info, serverData) {
    const wrap  = document.getElementById('invoicePreview');
    const inner = document.getElementById('invoicePreviewInner');
    const icon  = document.getElementById('invoicePreviewIcon');
    const main  = document.getElementById('invoicePreviewMain');
    const sub   = document.getElementById('invoicePreviewSub');
    const limit = document.getElementById('invoicePreviewLimit');
    const bar   = document.getElementById('invoicePreviewBar');
    const ltxt  = document.getElementById('invoicePreviewLimitText');

    if (!wrap) return;
    if (!info) { wrap.style.display = 'none'; return; }

    if (info.isOpen) {
      icon.className  = 'bi bi-check-circle-fill text-success fs-5 flex-shrink-0';
      inner.className = 'd-flex align-items-start gap-2 p-2 rounded border border-success bg-success bg-opacity-10';
      const closing   = info.daysToClosing !== null
        ? ` · fecha em ${info.daysToClosing} dia${info.daysToClosing !== 1 ? 's' : ''}`
        : '';
      main.innerHTML  = `<span class="text-success">✅ Vai cair na fatura de <strong>${info.invoiceLabel}</strong></span>`;
      sub.textContent = `Vence dia ${info.dueDay}${closing}`;
    } else {
      icon.className  = 'bi bi-arrow-right-circle-fill text-warning fs-5 flex-shrink-0';
      inner.className = 'd-flex align-items-start gap-2 p-2 rounded border border-warning bg-warning bg-opacity-10';
      main.innerHTML  = `<span class="text-warning">⚠️ Entra na fatura de <strong>${info.invoiceLabel}</strong></span>`;
      sub.textContent = `Fatura atual já fechou · próxima vence dia ${info.dueDay}`;
    }

    // Barra de limite (dados do servidor)
    const usage = serverData?.projected_usage ?? serverData?.current_usage;
    if (usage !== null && usage !== undefined && info.creditLimit) {
      const pct    = Math.min(usage / info.creditLimit * 100, 100);
      const bColor = pct > 80 ? 'bg-danger' : pct > 60 ? 'bg-warning' : 'bg-success';
      bar.style.width    = pct + '%';
      bar.className      = 'progress-bar ' + bColor;
      ltxt.innerHTML     = `Após essa compra: <strong>${_fmtBrl(usage)}</strong> / ${_fmtBrl(info.creditLimit)} (${pct.toFixed(0)}%)`;
      limit.style.display = '';
    } else {
      limit.style.display = 'none';
    }

    wrap.style.display = '';
  }

  async function updateInvoicePreview() {
    const method  = fPayment?.value;
    const cardId  = cardSelect?.value;
    const day     = parseInt(fDay?.value,   10);
    const month   = parseInt(fMonth?.value, 10);
    const year    = parseInt(fYear?.value,  10);
    const amount  = parseFloat(fAmount?.value) || 0;
    const wrap    = document.getElementById('invoicePreview');

    if (method !== 'Cartão de Crédito' || !cardId || !day || !month || !year) {
      if (wrap) wrap.style.display = 'none';
      return;
    }

    // Preview instantâneo a partir dos dados locais
    const info = _computeInvoice(cardId, day, month, year);
    _renderInvoice(info, null);

    // Busca dados de limite no servidor (debounced)
    clearTimeout(_invoiceTimer);
    _invoiceTimer = setTimeout(async () => {
      try {
        const p = new URLSearchParams({ card_id: cardId, day, month, year, amount });
        const res = await fetch('/cards/api/invoice-preview?' + p);
        if (!res.ok) return;
        const srv = await res.json();
        _renderInvoice(_computeInvoice(cardId, day, month, year), srv);
      } catch (_) {}
    }, 350);
  }

  // Listeners de atualização
  fPayment?.addEventListener('change', updateFields);
  form.querySelectorAll('input[name="credit_type"]').forEach(r =>
    r.addEventListener('change', () => { updateFields(); updateInstallmentHint(); })
  );
  cardSelect?.addEventListener('change', () => { autofillBankFromCard(); updateInvoicePreview(); });
  fDay?.addEventListener('input',    updateInvoicePreview);
  fMonth?.addEventListener('change', updateInvoicePreview);
  fYear?.addEventListener('change',  updateInvoicePreview);
  fAmount?.addEventListener('input', () => {
    updateInstallmentHint();
    clearTimeout(_invoiceTimer);
    _invoiceTimer = setTimeout(updateInvoicePreview, 350);
  });
  form.querySelector('#m_num_installments')?.addEventListener('change', updateInstallmentHint);

  recurringCheck?.addEventListener('change', () => {
    recurringRow?.classList.toggle('d-none', !recurringCheck.checked);
  });

  // ── Sugestão de categoria ───────────────────────────────────────
  let _catTimer = null;
  fDescription?.addEventListener('input', () => {
    clearTimeout(_catTimer);
    _catTimer = setTimeout(() => {
      const desc = fDescription.value.trim();
      if (desc.length < 3 || fCategory?.value.trim()) return;
      fetch('/api/chart/suggest-category?description=' + encodeURIComponent(desc))
        .then(r => r.json())
        .then(d => { if (d.category && !fCategory?.value.trim()) fCategory.value = d.category; })
        .catch(() => {});
    }, 400);
  });

  // ── Validação inline ───────────────────────────────────────────
  function clearErrors() {
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    form.querySelectorAll('.invalid-feedback').forEach(el => { el.textContent = ''; });
    errorAlert?.classList.add('d-none');
  }

  function showFieldError(name, message) {
    const field = form.querySelector(`#m_${name}`) || form.querySelector(`[name="${name}"]`);
    if (field) {
      field.classList.add('is-invalid');
      const fb = field.closest('.col-12, .col-sm-4, .col-sm-5, .col-sm-6, .col-4, .col-sm-2, .col-sm-3, .input-group')
                      ?.querySelector('.invalid-feedback')
                 || field.parentElement?.querySelector('.invalid-feedback');
      if (fb) fb.textContent = message;
    }
  }

  function showGlobalError(msg) {
    if (errorAlert) errorAlert.classList.remove('d-none');
    if (errorMsg) errorMsg.textContent = msg || 'Verifique os campos e tente novamente.';
  }

  // ── Submit via AJAX ────────────────────────────────────────────
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const label = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvando...';

    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: new FormData(form),
      });

      const data = await resp.json();

      if (data.status === 'ok') {
        bootstrap.Modal.getInstance(modalEl).hide();
        window.showToast?.(data.message || 'Despesa adicionada!', 'success');
        setTimeout(() => location.reload(), 800);
      } else {
        const errors = data.errors || {};
        let hasFieldError = false;
        for (const [field, msg] of Object.entries(errors)) {
          showFieldError(field, msg);
          hasFieldError = true;
        }
        if (!hasFieldError) showGlobalError(data.message);
        const advFields = ['bank','card_id','credit_type','num_installments',
                           'user_id','is_recurring','recurring_times'];
        if (advFields.some(f => errors[f]) && !advancedOpen) openAdvanced();
      }
    } catch (_) {
      showGlobalError('Erro de conexão. Tente novamente.');
    } finally {
      saveBtn.disabled = false;
      saveBtn.innerHTML = label;
    }
  });

  // ── Reset ao fechar o modal ────────────────────────────────────
  modalEl.addEventListener('hidden.bs.modal', () => {
    form.reset();
    clearErrors();
    closeAdvanced();
    updateFields();
  });

  // ── Inicializar data com hoje quando modal abre ────────────────
  modalEl.addEventListener('show.bs.modal', () => {
    const today = new Date();
    if (fDay)   fDay.value   = today.getDate();
    if (fMonth) fMonth.value = today.getMonth() + 1;
    if (fYear)  fYear.value  = today.getFullYear();
    setTimeout(() => fDescription?.focus(), 200);
  });

  // Estado inicial
  updateFields();
})();
