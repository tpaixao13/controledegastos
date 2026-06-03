/**
 * FinFam — Goals AJAX handler
 * Intercepta submits dos modais de metas e executa via AJAX.
 * Fallback: se JS desativado, os forms funcionam como POST normal.
 */

(() => {
  // ── Helpers ───────────────────────────────────────────────────────
  function showBtn(btn, html) {
    btn.disabled = false;
    btn.innerHTML = html;
  }

  function spinBtn(btn) {
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
    return orig;
  }

  function closeModal(formEl) {
    const modalEl = formEl.closest('.modal');
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();
  }

  async function submitGoalForm(form, { onSuccess, onError } = {}) {
    const btn  = form.querySelector('[type="submit"]');
    const orig = spinBtn(btn);

    try {
      const resp = await fetch(form.action, {
        method:  'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body:    new FormData(form),
      });

      let data;
      try { data = await resp.json(); }
      catch { data = { status: 'error', message: 'Resposta inesperada do servidor.' }; }

      if (!resp.ok || data.status !== 'ok') {
        window.showToast?.(data.message || 'Erro ao processar ação.', 'danger');
        onError?.();
        return;
      }

      closeModal(form);
      window.showToast?.(data.message, 'success');
      onSuccess?.();

    } catch {
      window.showToast?.('Erro de conexão. Tente novamente.', 'danger');
      onError?.();
    } finally {
      showBtn(btn, orig);
    }
  }

  // ── Ação: Concluir ────────────────────────────────────────────────
  const formComplete = document.getElementById('formComplete');
  if (formComplete) {
    formComplete.addEventListener('submit', async (e) => {
      e.preventDefault();
      await submitGoalForm(formComplete, {
        onSuccess: () => {
          // Atualizar o card visualmente antes do reload
          const goalId = formComplete.action.split('/').pop();
          const card   = document.getElementById(`goal-card-${goalId}`);
          if (card) {
            card.classList.add('border-success', 'border-opacity-50', 'opacity-75');
            const footer = card.querySelector('.card-footer');
            if (footer) {
              footer.innerHTML = `
                <div class="text-center text-success small fw-semibold">
                  <i class="bi bi-trophy-fill me-1"></i>Meta concluída!
                </div>`;
            }
          }
          setTimeout(() => location.reload(), 900);
        },
      });
    });
  }

  // ── Ação: Arquivar ────────────────────────────────────────────────
  const formDelete = document.getElementById('formDelete');
  if (formDelete) {
    formDelete.addEventListener('submit', async (e) => {
      e.preventDefault();
      await submitGoalForm(formDelete, {
        onSuccess: () => {
          const goalId = formDelete.action.split('/').pop();
          const col    = document.getElementById(`goal-card-${goalId}`)?.closest('.col-md-6, .col-xl-4');
          if (col) {
            col.style.transition = 'opacity .35s, transform .35s';
            col.style.opacity    = '0';
            col.style.transform  = 'scale(.95)';
            setTimeout(() => col.remove(), 380);
          } else {
            setTimeout(() => location.reload(), 700);
          }
        },
      });
    });
  }

  // ── Ação: Editar ──────────────────────────────────────────────────
  const formEdit = document.getElementById('formEditGoal');
  if (formEdit) {
    formEdit.addEventListener('submit', async (e) => {
      e.preventDefault();
      await submitGoalForm(formEdit, {
        onSuccess: () => setTimeout(() => location.reload(), 700),
      });
    });
  }

  // ── Ação: Nova Meta ───────────────────────────────────────────────
  const formAdd = document.querySelector('#modalAddGoal form');
  if (formAdd) {
    formAdd.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorDiv = formAdd.querySelector('.goal-form-error');
      if (errorDiv) errorDiv.classList.add('d-none');

      await submitGoalForm(formAdd, {
        onSuccess: () => setTimeout(() => location.reload(), 700),
        onError:   () => {
          if (errorDiv) errorDiv.classList.remove('d-none');
        },
      });
    });
  }
})();
