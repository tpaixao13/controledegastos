/**
 * FinFam — Goals AJAX handler
 */
document.addEventListener('DOMContentLoaded', () => {

  async function goalAction(form) {
    // Verificação defensiva: form.action deve apontar para um endpoint de metas
    if (!form.action || form.action === window.location.href) {
      console.error('[goals.js] form.action não configurado:', form.action);
      window.showToast?.('Erro: ação não configurada. Tente novamente.', 'danger');
      return;
    }

    const btn      = form.querySelector('[type="submit"]');
    const origHtml = btn?.innerHTML ?? '';
    if (btn) {
      btn.disabled  = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }

    try {
      const csrfToken = form.querySelector('[name="csrf_token"]')?.value ?? '';

      const resp = await fetch(form.action, {
        method:  'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken':       csrfToken,
        },
        body: new FormData(form),
      });

      // Tentar parsear JSON; se falhar mostrar erro legível
      let data;
      try {
        data = await resp.json();
      } catch {
        const text = await resp.text().catch(() => '');
        console.error('[goals.js] Resposta não é JSON. Status:', resp.status, text.slice(0, 200));
        window.showToast?.(`Erro ${resp.status} ao processar ação.`, 'danger');
        return;
      }

      if (!resp.ok || data.status !== 'ok') {
        window.showToast?.(data.message || `Erro ${resp.status}.`, 'danger');
        return;
      }

      // Fechar modal
      const modalEl = form.closest('.modal');
      if (modalEl) {
        (bootstrap.Modal.getInstance(modalEl) ?? bootstrap.Modal.getOrCreate(modalEl)).hide();
      }

      window.showToast?.(data.message, 'success');
      return true; // sinaliza sucesso para o caller

    } catch (err) {
      console.error('[goals.js] Erro na requisição:', err);
      window.showToast?.('Erro de conexão. Tente novamente.', 'danger');
      return false;
    } finally {
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = origHtml;
      }
    }
  }

  // ── Concluir ──────────────────────────────────────────────────────
  document.getElementById('formComplete')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const ok = await goalAction(e.target);
    if (ok) {
      const goalId = e.target.action.split('/').pop();
      const card   = document.getElementById(`goal-card-${goalId}`);
      if (card) {
        card.classList.add('border-success', 'border-opacity-50');
        card.style.opacity = '.6';
        const footer = card.querySelector('.card-footer');
        if (footer) footer.innerHTML =
          '<div class="text-center text-success small fw-semibold py-1">' +
          '<i class="bi bi-trophy-fill me-1"></i>Meta concluída!</div>';
      }
      setTimeout(() => location.reload(), 900);
    }
  });

  // ── Arquivar ──────────────────────────────────────────────────────
  document.getElementById('formDelete')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const ok = await goalAction(e.target);
    if (ok) {
      const goalId = e.target.action.split('/').pop();
      const col    = document.getElementById(`goal-card-${goalId}`)
                              ?.closest('.col-md-6, .col-xl-4');
      if (col) {
        col.style.transition = 'opacity .35s, transform .35s';
        col.style.opacity    = '0';
        col.style.transform  = 'scale(.95)';
        setTimeout(() => col.remove(), 400);
      } else {
        setTimeout(() => location.reload(), 700);
      }
    }
  });

  // ── Editar ────────────────────────────────────────────────────────
  document.getElementById('formEditGoal')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const ok = await goalAction(e.target);
    if (ok) setTimeout(() => location.reload(), 700);
  });

  // ── Nova Meta ─────────────────────────────────────────────────────
  document.querySelector('#modalAddGoal form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errDiv = e.target.querySelector('.goal-form-error');
    errDiv?.classList.add('d-none');
    const ok = await goalAction(e.target);
    if (ok) {
      setTimeout(() => location.reload(), 700);
    } else {
      errDiv?.classList.remove('d-none');
    }
  });

});
