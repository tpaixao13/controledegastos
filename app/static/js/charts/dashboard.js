/**
 * FinFam — Dashboard Charts
 * Todos os gráficos do dashboard, organizados em funções independentes.
 */

document.addEventListener('DOMContentLoaded', () => {
  const month  = document.getElementById('chart-month')?.value;
  const year   = document.getElementById('chart-year')?.value;
  if (!month || !year) return;

  const params = `?month=${month}&year=${year}`;

  // ── Utilitários ──────────────────────────────────────────────
  function brl(v) {
    return 'R$ ' + parseFloat(v).toLocaleString('pt-BR', {
      minimumFractionDigits: 2, maximumFractionDigits: 2,
    });
  }

  const FONT = { family: "'Segoe UI', system-ui, sans-serif", size: 12 };

  const BASE_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { font: FONT, boxWidth: 12 } },
      tooltip: { bodyFont: FONT, titleFont: { ...FONT, weight: '600' } },
    },
    scales: {},
  };

  function moneyTooltip() {
    return {
      plugins: {
        tooltip: {
          callbacks: { label: ctx => `${ctx.dataset.label || ''}: ${brl(ctx.parsed.y ?? ctx.parsed)}` },
        },
      },
    };
  }

  // ── 1. Gastos por Categoria (Doughnut) ───────────────────────
  function initCategoryChart() {
    fetch('/api/chart/doughnut' + params)
      .then(r => r.json())
      .then(d => {
        const ctx = document.getElementById('chartDoughnut');
        if (!ctx) return;

        const salary = d.total_salary || 0;
        const total  = d.data.reduce((a, b) => a + b, 0);

        const labels = d.labels.map((lbl, i) => {
          const pct = total > 0 ? (d.data[i] / total * 100).toFixed(1) : 0;
          return `${lbl} (${pct}%)`;
        });

        new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels,
            datasets: [{ data: d.data, backgroundColor: d.colors, borderWidth: 2 }],
          },
          options: {
            ...BASE_OPTIONS,
            cutout: '62%',
            plugins: {
              legend: { position: 'right', labels: { font: FONT, boxWidth: 12 } },
              tooltip: {
                callbacks: {
                  label: ctx => {
                    const val = ctx.parsed;
                    const pctTotal = total > 0 ? (val / total * 100).toFixed(1) : 0;
                    const lines = [`${brl(val)} · ${pctTotal}% dos gastos`];
                    if (salary > 0) lines.push(`${(val / salary * 100).toFixed(1)}% do salário`);
                    return lines;
                  },
                },
              },
            },
          },
        });
      });
  }

  // ── 2. Receita vs Gastos (Bar agrupado) ─────────────────────
  let _cashflowChart = null;
  function initCashflowChart(months = 6) {
    fetch(`/api/chart/monthly-vs-salary?months=${months}&month=${month}&year=${year}`)
      .then(r => r.json())
      .then(d => {
        const ctx = document.getElementById('chartMonthly');
        if (!ctx) return;
        if (_cashflowChart) _cashflowChart.destroy();

        _cashflowChart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: d.labels,
            datasets: [
              {
                label: 'Receita',
                data: d.salarios,
                backgroundColor: 'rgba(25,135,84,.65)',
                borderColor: '#198754',
                borderWidth: 1,
                borderRadius: 4,
              },
              {
                label: 'Gastos',
                data: d.gastos,
                backgroundColor: 'rgba(220,53,69,.65)',
                borderColor: '#dc3545',
                borderWidth: 1,
                borderRadius: 4,
              },
            ],
          },
          options: {
            ...BASE_OPTIONS,
            ...moneyTooltip(),
            scales: {
              x: { grid: { display: false } },
              y: { ticks: { callback: v => 'R$ ' + v.toLocaleString('pt-BR') } },
            },
          },
        });
      });
  }

  // ── 3. Evolução Diária (Line com área) ───────────────────────
  function initTimelineChart() {
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
              backgroundColor: 'rgba(220,53,69,.07)',
              fill: true,
              tension: 0.35,
              pointRadius: 3,
              pointHoverRadius: 5,
              borderWidth: 2,
            }],
          },
          options: {
            ...BASE_OPTIONS,
            ...moneyTooltip(),
            scales: {
              x: { grid: { display: false } },
              y: { ticks: { callback: v => 'R$ ' + v.toLocaleString('pt-BR') } },
            },
          },
        });
      });
  }

  // ── 4. Formas de Pagamento (Doughnut) ────────────────────────
  let _paymentChart = null;
  function initPaymentChart(months = 1) {
    fetch(`/api/chart/payment-methods?months=${months}&month=${month}&year=${year}`)
      .then(r => r.json())
      .then(d => {
        const ctx = document.getElementById('chartPayments');
        if (!ctx) return;
        if (_paymentChart) _paymentChart.destroy();

        // Agrega totais por método ao longo do período
        const agg = d.datasets
          .map(ds => ({
            label: ds.label,
            total: ds.data.reduce((a, b) => a + b, 0),
            color: ds.backgroundColor,
          }))
          .filter(x => x.total > 0);

        const grandTotal = agg.reduce((a, x) => a + x.total, 0);

        _paymentChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: agg.map(x => x.label),
            datasets: [{
              data:            agg.map(x => x.total),
              backgroundColor: agg.map(x => x.color),
              borderWidth: 2,
            }],
          },
          options: {
            ...BASE_OPTIONS,
            cutout: '62%',
            plugins: {
              legend: {
                position: 'right',
                labels: {
                  font: FONT,
                  boxWidth: 12,
                  generateLabels: chart => agg.map((x, i) => ({
                    text:        `${x.label} — ${brl(x.total)}`,
                    fillStyle:   x.color,
                    strokeStyle: x.color,
                    lineWidth:   0,
                    hidden:      false,
                    index:       i,
                  })),
                },
              },
              tooltip: {
                callbacks: {
                  label: ctx => {
                    const pct = grandTotal > 0 ? (ctx.parsed / grandTotal * 100).toFixed(1) : 0;
                    return `${brl(ctx.parsed)} (${pct}%)`;
                  },
                },
              },
            },
          },
        });
      });
  }

  // ── 5. Pago vs Pendente (Doughnut) ──────────────────────────
  function initPendingChart() {
    fetch('/api/chart/pending-vs-paid' + params)
      .then(r => r.json())
      .then(d => {
        const ctx = document.getElementById('chartPending');
        if (!ctx) return;

        new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: d.labels,
            datasets: [{ data: d.data, backgroundColor: d.colors, borderWidth: 2 }],
          },
          options: {
            ...BASE_OPTIONS,
            cutout: '62%',
            plugins: {
              legend: { position: 'right', labels: { font: FONT, boxWidth: 12 } },
              tooltip: {
                callbacks: { label: ctx => `${ctx.label}: ${brl(ctx.parsed)}` },
              },
            },
          },
        });
      });
  }

  // ── 6. Comparação por usuário (Bar) ─────────────────────────
  function initUsersChart() {
    fetch('/api/chart/user-comparison' + params)
      .then(r => r.json())
      .then(d => {
        const ctx = document.getElementById('chartUsers');
        if (!ctx) return;

        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: d.labels,
            datasets: [{
              label: 'Gastos',
              data: d.gastos,
              backgroundColor: d.colors,
              borderColor: d.border_colors,
              borderWidth: 1,
              borderRadius: 4,
            }],
          },
          options: {
            ...BASE_OPTIONS,
            ...moneyTooltip(),
            plugins: {
              legend: {
                labels: {
                  generateLabels: chart => chart.data.labels.map((name, i) => ({
                    text: name,
                    fillStyle: chart.data.datasets[0].backgroundColor[i],
                    strokeStyle: chart.data.datasets[0].borderColor[i],
                    lineWidth: 1,
                    hidden: false,
                  })),
                },
              },
              tooltip: { callbacks: { label: ctx => brl(ctx.parsed.y ?? ctx.parsed) } },
            },
            scales: { x: { grid: { display: false } } },
          },
        });
      });
  }

  // ── Inicialização ────────────────────────────────────────────
  initCategoryChart();
  initCashflowChart(6);
  initTimelineChart();
  initPaymentChart(1);
  initPendingChart();
  initUsersChart();

  // ── Controles de período ─────────────────────────────────────
  document.querySelectorAll('#monthlyPeriod button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#monthlyPeriod button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      initCashflowChart(btn.dataset.months);
    });
  });

  document.querySelectorAll('#paymentsPeriod button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#paymentsPeriod button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      initPaymentChart(btn.dataset.months);
    });
  });
});
