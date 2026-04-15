document.addEventListener('DOMContentLoaded', function () {
  const month = document.getElementById('chart-month').value;
  const year = document.getElementById('chart-year').value;
  const params = `?month=${month}&year=${year}`;

  // Utilitário: formatar R$
  function brl(v) {
    return 'R$ ' + parseFloat(v).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }

  const tooltipBRL = {
    plugins: {
      tooltip: {
        callbacks: {
          label: ctx => brl(ctx.parsed.y ?? ctx.parsed)
        }
      }
    }
  };

  // 1 — Doughnut: gastos por categoria
  fetch('/api/chart/doughnut' + params)
    .then(r => r.json())
    .then(d => {
      const ctx = document.getElementById('chartDoughnut');
      if (!ctx) return;
      new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: d.labels,
          datasets: [{
            data: d.data,
            backgroundColor: d.colors,
            borderWidth: 2,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right' },
            tooltip: {
              callbacks: {
                label: ctx => `${ctx.label}: ${brl(ctx.parsed)}`
              }
            }
          }
        }
      });
    });

  // 2 — Barras: gastos vs salário (últimos 6 meses)
  fetch('/api/chart/monthly-vs-salary')
    .then(r => r.json())
    .then(d => {
      const ctx = document.getElementById('chartMonthly');
      if (!ctx) return;
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: d.labels,
          datasets: [
            {
              label: 'Salário',
              data: d.salarios,
              backgroundColor: 'rgba(25, 135, 84, 0.6)',
              borderColor: '#198754',
              borderWidth: 1,
            },
            {
              label: 'Gastos',
              data: d.gastos,
              backgroundColor: 'rgba(220, 53, 69, 0.6)',
              borderColor: '#dc3545',
              borderWidth: 1,
            }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false, ...tooltipBRL }
      });
    });

  // 3 — Barras: comparação Tiago vs Greyce
  fetch('/api/chart/user-comparison' + params)
    .then(r => r.json())
    .then(d => {
      const ctx = document.getElementById('chartUsers');
      if (!ctx) return;
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: d.labels,
          datasets: [
            {
              label: 'Gastos',
              data: d.gastos,
              backgroundColor: ['rgba(13,110,253,0.7)', 'rgba(214,51,132,0.7)'],
              borderColor: ['#0d6efd', '#d63384'],
              borderWidth: 1,
            }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false, ...tooltipBRL }
      });
    });

  // 4 — Linha: evolução diária
  fetch('/api/chart/daily' + params)
    .then(r => r.json())
    .then(d => {
      const ctx = document.getElementById('chartDaily');
      if (!ctx) return;
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: d.labels,
          datasets: [{
            label: 'Acumulado',
            data: d.data,
            borderColor: '#fd7e14',
            backgroundColor: 'rgba(253,126,20,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, ...tooltipBRL }
      });
    });

  // 5 — Barras empilhadas: forma de pagamento por mês
  fetch('/api/chart/payment-methods')
    .then(r => r.json())
    .then(d => {
      const ctx = document.getElementById('chartPayments');
      if (!ctx) return;
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: d.labels,
          datasets: d.datasets,
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { x: { stacked: true }, y: { stacked: true } },
          ...tooltipBRL
        }
      });
    });
});
