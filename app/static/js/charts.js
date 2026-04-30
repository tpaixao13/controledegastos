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
      const salary = d.total_salary || 0;
      const totalExpenses = d.data.reduce((a, b) => a + b, 0);

      // Labels com % do salário
      const labelsWithPct = d.labels.map((lbl, i) => {
        if (salary > 0) {
          const pct = (d.data[i] / salary * 100).toFixed(1);
          return `${lbl} (${pct}% sal.)`;
        }
        return lbl;
      });

      new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labelsWithPct,
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
            legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } },
            tooltip: {
              callbacks: {
                label: ctx => {
                  const val = ctx.parsed;
                  const pctTotal = totalExpenses > 0 ? (val / totalExpenses * 100).toFixed(1) : 0;
                  const pctSal = salary > 0 ? (val / salary * 100).toFixed(1) : null;
                  const lines = [`${brl(val)} (${pctTotal}% dos gastos)`];
                  if (pctSal) lines.push(`${pctSal}% do salário`);
                  return lines;
                }
              }
            }
          }
        }
      });
    });

  // 2 — Barras: gastos vs salário (período dinâmico)
  let chartMonthlyInst = null;
  function loadChartMonthly(months) {
    fetch(`/api/chart/monthly-vs-salary?months=${months}&month=${month}&year=${year}`)
      .then(r => r.json())
      .then(d => {
        const ctx = document.getElementById('chartMonthly');
        if (!ctx) return;
        if (chartMonthlyInst) chartMonthlyInst.destroy();
        chartMonthlyInst = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: d.labels,
            datasets: [
              { label: 'Salário', data: d.salarios, backgroundColor: 'rgba(25,135,84,0.6)', borderColor: '#198754', borderWidth: 1 },
              { label: 'Gastos', data: d.gastos, backgroundColor: 'rgba(220,53,69,0.6)', borderColor: '#dc3545', borderWidth: 1 }
            ]
          },
          options: { responsive: true, maintainAspectRatio: false, ...tooltipBRL }
        });
      });
  }
  loadChartMonthly(1);
  document.querySelectorAll('#monthlyPeriod button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#monthlyPeriod button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadChartMonthly(btn.dataset.months);
    });
  });

  // 3 — Barras: comparação por usuário
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
              backgroundColor: d.colors,
              borderColor: d.border_colors,
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
            borderColor: '#dc3545',
            backgroundColor: 'rgba(220,53,69,0.08)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, ...tooltipBRL }
      });
    });

  // 5 — Doughnut: pago vs pendente
  fetch('/api/chart/pending-vs-paid' + params)
    .then(r => r.json())
    .then(d => {
      const ctx = document.getElementById('chartPending');
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

  // 6 — Barras empilhadas: forma de pagamento (período dinâmico)
  let chartPaymentsInst = null;
  function loadChartPayments(months) {
    fetch(`/api/chart/payment-methods?months=${months}&month=${month}&year=${year}`)
      .then(r => r.json())
      .then(d => {
        const ctx = document.getElementById('chartPayments');
        if (!ctx) return;
        if (chartPaymentsInst) chartPaymentsInst.destroy();
        chartPaymentsInst = new Chart(ctx, {
          type: 'bar',
          data: { labels: d.labels, datasets: d.datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { x: { stacked: true }, y: { stacked: true } },
            ...tooltipBRL
          }
        });
      });
  }
  loadChartPayments(1);
  document.querySelectorAll('#paymentsPeriod button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#paymentsPeriod button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadChartPayments(btn.dataset.months);
    });
  });
});
