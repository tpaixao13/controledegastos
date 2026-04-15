document.addEventListener('DOMContentLoaded', function () {
  const paymentSelect = document.getElementById('payment_method');
  const bankRow = document.getElementById('bank-row');
  const installmentSection = document.getElementById('installment-section');
  const numInstallmentsRow = document.getElementById('num-installments-row');
  const creditTypeRadios = document.querySelectorAll('input[name="credit_type"]');

  function updateForm() {
    const method = paymentSelect.value;

    if (method === 'Cartão de Débito') {
      bankRow.style.display = '';
      installmentSection.style.display = 'none';
    } else if (method === 'Cartão de Crédito') {
      bankRow.style.display = '';
      installmentSection.style.display = '';
      updateInstallments();
    } else {
      // PIX ou Dinheiro
      bankRow.style.display = 'none';
      installmentSection.style.display = 'none';
    }
  }

  function updateInstallments() {
    const parcelado = document.querySelector('input[name="credit_type"]:checked');
    if (parcelado && parcelado.value === 'parcelado') {
      numInstallmentsRow.style.display = '';
    } else {
      numInstallmentsRow.style.display = 'none';
    }
  }

  paymentSelect.addEventListener('change', updateForm);
  creditTypeRadios.forEach(r => r.addEventListener('change', updateInstallments));

  // Estado inicial
  updateForm();
});
