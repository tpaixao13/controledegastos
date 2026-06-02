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

  // Avançados
  const bankRow         = form.querySelector('#m_bank_row');
  const cardRow         = form.querySelector('#m_card_row');
  const cardSelect      = form.querySelector('#m_card_id');
  const billingHint     = form.querySelector('#m_billing_hint');
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
  const _BANK_METHODS = ['PIX', 'Cartão de Débito', 'Cartão de Crédito', 'VR', 'VA'];

  function updateFields() {
    const method = fPayment?.value || '';
    const isCredit   = method === 'Cartão de Crédito';
    const needsBank  = _BANK_METHODS.includes(method);
    const isParcelado = form.querySelector('#m_credit_parcelado')?.checked;

    // Banco
    bankRow?.classList.toggle('d-none', !needsBank);

    // Cartão + tipo crédito
    cardRow?.classList.toggle('d-none', !isCredit);
    creditTypeRow?.classList.toggle('d-none', !isCredit);

    // Parcelas
    installmentsRow?.classList.toggle('d-none', !(isCredit && isParcelado));

    // Hint de fatura
    updateBillingHint();
  }

  function updateBillingHint() {
    if (!billingHint || !cardSelect || !fDay || !fMonth) {
      return;
    }
    const id  = parseInt(cardSelect.value, 10);
    const card = cardData[id];
    if (!card || !id) { billingHint.style.display = 'none'; return; }

    const day   = parseInt(fDay.value, 10);
    const month = parseInt(fMonth.value, 10);
    if (!day || !month) { billingHint.style.display = 'none'; return; }

    const billingMonth = day > card.best_buy_day
      ? (month === 12 ? 1 : month + 1)
      : month;

    const icon = day > card.best_buy_day
      ? '<i class="bi bi-arrow-right-circle"></i>'
      : '<i class="bi bi-check-circle"></i>';

    billingHint.innerHTML = `${icon} Esta compra entra na fatura de <strong>${MONTH_NAMES[billingMonth - 1]}</strong> (vence dia ${card.due_day}).`;
    billingHint.style.display = '';
  }

  // Listeners de atualização
  fPayment?.addEventListener('change', updateFields);

  form.querySelectorAll('input[name="credit_type"]').forEach(r => {
    r.addEventListener('change', updateFields);
  });

  cardSelect?.addEventListener('change', updateBillingHint);
  fDay?.addEventListener('input', updateBillingHint);
  fMonth?.addEventListener('change', updateBillingHint);

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
    // Tenta pelo id (m_<name>) ou pelo name
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
        // Erros de validação por campo
        const errors = data.errors || {};
        let hasFieldError = false;
        for (const [field, msg] of Object.entries(errors)) {
          showFieldError(field, msg);
          hasFieldError = true;
        }
        if (!hasFieldError) showGlobalError(data.message);
        // Abre seção avançada se o erro estiver lá
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
    if (fDay && !fDay.value)   fDay.value   = today.getDate();
    if (fMonth && !fMonth.value) fMonth.value = today.getMonth() + 1;
    if (fYear && !fYear.value)   fYear.value  = today.getFullYear();
    // Focar na descrição
    setTimeout(() => fDescription?.focus(), 200);
  });

  // Estado inicial
  updateFields();
})();
