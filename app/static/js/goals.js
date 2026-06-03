/**
 * FinFam — Goals actions (edit, complete, archive, add)
 * Segue o mesmo padrão do expense_modal.js que funciona.
 */
(() => {
  // ── Helper: envia form via AJAX e retorna true/false ──────────────
  async function postForm(form) {
    if (!form) return false;

    const btn      = form.querySelector('[type="submit"]');
    const origHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled  = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }

    try {
      const resp = await fetch(form.action, {
        method:  'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body:    new FormData(form),
      });

      const data = await resp.json();

      if (data.status === 'ok') {
        const modalEl = form.closest('.modal');
        if (modalEl) {
          const inst = bootstrap.Modal.getInstance(modalEl);
          if (inst) inst.hide();
        }
        window.showToast?.(data.message, 'success');
        return true;
      }

      window.showToast?.(data.message || 'Erro ao processar.', 'danger');
      return false;

    } catch (err) {
      console.error('[goals]', err);
      window.showToast?.('Erro de conexão. Tente novamente.', 'danger');
      return false;
    } finally {
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = origHtml;
      }
    }
  }

  // ── Validar que o form tem action apontando para /goals/ ──────────
  function validAction(form) {
    return form && /\/goals\/(edit|complete|delete|add)/.test(form.action || '');
  }

  // ── Concluir ──────────────────────────────────────────────────────
  const fComplete = document.getElementById('formComplete');
  if (fComplete) {
    fComplete.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!validAction(fComplete)) { fComplete.submit(); return; }
      const ok = await postForm(fComplete);
      if (ok) setTimeout(() => location.reload(), 700);
    });
  }

  // ── Arquivar ──────────────────────────────────────────────────────
  const fDelete = document.getElementById('formDelete');
  if (fDelete) {
    fDelete.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!validAction(fDelete)) { fDelete.submit(); return; }
      const ok = await postForm(fDelete);
      if (ok) {
        const goalId = fDelete.action.split('/').pop();
        const col    = document.getElementById('goal-card-' + goalId)
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
  }

  // ── Editar ────────────────────────────────────────────────────────
  const fEdit = document.getElementById('formEditGoal');
  if (fEdit) {
    fEdit.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!validAction(fEdit)) { fEdit.submit(); return; }
      const ok = await postForm(fEdit);
      if (ok) setTimeout(() => location.reload(), 700);
    });
  }

  // ── Nova Meta ─────────────────────────────────────────────────────
  const fAdd = document.querySelector('#modalAddGoal form');
  if (fAdd) {
    fAdd.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!validAction(fAdd)) { fAdd.submit(); return; }
      const errDiv = fAdd.querySelector('.goal-form-error');
      errDiv?.classList.add('d-none');
      const ok = await postForm(fAdd);
      if (ok) setTimeout(() => location.reload(), 700);
      else errDiv?.classList.remove('d-none');
    });
  }

})();
