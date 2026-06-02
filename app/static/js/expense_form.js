document.addEventListener('DOMContentLoaded', function () {
  const paymentSelect = document.getElementById('payment_method');
  const bankRow = document.getElementById('bank-row');
  const cardRow = document.getElementById('card-row');
  const cardSelect = document.getElementById('card_id');
  const billingHint = document.getElementById('billing-hint');
  const installmentSection = document.getElementById('installment-section');
  const numInstallmentsRow = document.getElementById('num-installments-row');
  const creditTypeRadios = document.querySelectorAll('input[name="credit_type"]');
  const recurringCheck = document.getElementById('is_recurring');
  const recurringTimesRow = document.getElementById('recurring-times-row');
  const dayInput = document.querySelector('input[name="day"]');
  const monthSelect = document.querySelector('select[name="month"]');

  // Dados dos cartões injetados pelo template (preenchido na rota)
  const cardData = window._cardData || {};

  const MONTH_NAMES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                       'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

  function updateForm() {
    const method = paymentSelect ? paymentSelect.value : '';

    if (['Cartão de Débito', 'PIX', 'VR', 'VA'].includes(method)) {
      if (bankRow) bankRow.style.display = '';
      if (cardRow) cardRow.style.display = 'none';
      if (installmentSection) installmentSection.style.display = 'none';
      if (numInstallmentsRow) numInstallmentsRow.style.display = 'none';
    } else if (method === 'Cartão de Crédito') {
      if (bankRow) bankRow.style.display = '';
      if (cardRow) cardRow.style.display = '';
      if (installmentSection) installmentSection.style.display = '';
      updateInstallments();
      updateBillingHint();
    } else {
      if (bankRow) bankRow.style.display = 'none';
      if (cardRow) cardRow.style.display = 'none';
      if (installmentSection) installmentSection.style.display = 'none';
      if (numInstallmentsRow) numInstallmentsRow.style.display = 'none';
    }
  }

  function updateInstallments() {
    const parcelado = document.querySelector('input[name="credit_type"]:checked');
    if (parcelado && parcelado.value === 'parcelado') {
      if (numInstallmentsRow) numInstallmentsRow.style.display = '';
    } else {
      if (numInstallmentsRow) numInstallmentsRow.style.display = 'none';
    }
  }

  function updateRecurring() {
    if (!recurringTimesRow) return;
    if (recurringCheck && recurringCheck.checked) {
      recurringTimesRow.style.display = '';
    } else {
      recurringTimesRow.style.display = 'none';
    }
  }

  function updateBillingHint() {
    if (!billingHint || !cardSelect || !dayInput || !monthSelect) return;
    const cardId = parseInt(cardSelect.value, 10);
    const card = cardData[cardId];
    if (!card || !cardId) {
      billingHint.style.display = 'none';
      return;
    }
    const purchaseDay = parseInt(dayInput.value, 10);
    const purchaseMonth = parseInt(monthSelect.value, 10);
    if (!purchaseDay || !purchaseMonth) {
      billingHint.style.display = 'none';
      return;
    }

    let billingMonth = purchaseMonth;
    if (purchaseDay > card.best_buy_day) {
      billingMonth = purchaseMonth === 12 ? 1 : purchaseMonth + 1;
    }

    const monthName = MONTH_NAMES[billingMonth - 1];
    const icon = purchaseDay > card.best_buy_day
      ? '<i class="bi bi-arrow-right-circle"></i>'
      : '<i class="bi bi-check-circle"></i>';
    billingHint.innerHTML = `${icon} Esta compra entra na fatura de <strong>${monthName}</strong> (vence dia ${card.due_day}).`;
    billingHint.style.display = '';
  }

  if (paymentSelect) paymentSelect.addEventListener('change', updateForm);
  creditTypeRadios.forEach(r => r.addEventListener('change', updateInstallments));
  if (recurringCheck) recurringCheck.addEventListener('change', updateRecurring);
  if (cardSelect) cardSelect.addEventListener('change', updateBillingHint);
  if (dayInput) dayInput.addEventListener('input', updateBillingHint);
  if (monthSelect) monthSelect.addEventListener('change', updateBillingHint);

  updateForm();
  updateRecurring();

  // Sugestão automática de categoria
  const descInput = document.getElementById('description');
  const categoryInput = document.getElementById('category');
  let _suggestTimer = null;

  function _fetchCategoryHint() {
    if (!descInput || !categoryInput || categoryInput.value.trim()) return;
    const desc = descInput.value.trim();
    if (desc.length < 3) return;
    fetch('/api/chart/suggest-category?description=' + encodeURIComponent(desc))
      .then(r => r.json())
      .then(data => {
        if (data.category && !categoryInput.value.trim()) {
          categoryInput.value = data.category;
        }
      })
      .catch(() => {});
  }

  if (descInput) {
    descInput.addEventListener('input', function () {
      clearTimeout(_suggestTimer);
      _suggestTimer = setTimeout(_fetchCategoryHint, 400);
    });
  }
});
