document.addEventListener('DOMContentLoaded', function () {
  const paymentSelect = document.getElementById('payment_method');
  const bankRow = document.getElementById('bank-row');
  const installmentSection = document.getElementById('installment-section');
  const numInstallmentsRow = document.getElementById('num-installments-row');
  const creditTypeRadios = document.querySelectorAll('input[name="credit_type"]');
  const recurringCheck = document.getElementById('is_recurring');
  const recurringTimesRow = document.getElementById('recurring-times-row');

  function updateForm() {
    const method = paymentSelect ? paymentSelect.value : '';

    if (method === 'Cartão de Débito' || method === 'PIX') {
      if (bankRow) bankRow.style.display = '';
      if (installmentSection) installmentSection.style.display = 'none';
      if (numInstallmentsRow) numInstallmentsRow.style.display = 'none';
    } else if (method === 'Cartão de Crédito') {
      if (bankRow) bankRow.style.display = '';
      if (installmentSection) installmentSection.style.display = '';
      updateInstallments();
    } else {
      // Dinheiro ou vazio
      if (bankRow) bankRow.style.display = 'none';
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

  if (paymentSelect) paymentSelect.addEventListener('change', updateForm);
  creditTypeRadios.forEach(r => r.addEventListener('change', updateInstallments));
  if (recurringCheck) recurringCheck.addEventListener('change', updateRecurring);

  // Estado inicial
  updateForm();
  updateRecurring();
});
