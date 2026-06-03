"""
Correção de despesas duplicadas no mesmo mês.

Regras:
  1. Grupo (installment/recurring): para cada par de entradas do mesmo grupo
     no mesmo mês, mantém a de menor número e empurra a seguinte para o mês seguinte.
  2. Recorrente + Simples: mantém a recorrente, empurra a simples para o mês seguinte.

Execute com: python fix_duplicates.py
"""

from app import create_app, db
from app.models import Expense
from app.utils import month_offset
from sqlalchemy import text

app = create_app()


def fix():
    with app.app_context():
        moved = 0

        # ── 1. Mesmo grupo (installment ou recurring) no mesmo mês ────────
        rows = db.session.execute(text("""
            SELECT a.id AS id_a, b.id AS id_b,
                   a.installment_number AS num_a, b.installment_number AS num_b,
                   a.recurring_number   AS rnum_a, b.recurring_number   AS rnum_b,
                   a.month, a.year, a.description
            FROM expenses a
            JOIN expenses b
              ON  a.user_id  = b.user_id
              AND a.month    = b.month
              AND a.year     = b.year
              AND a.id       < b.id
              AND (
                    (a.installment_group_id IS NOT NULL
                     AND a.installment_group_id = b.installment_group_id)
                 OR (a.recurring_group_id IS NOT NULL
                     AND a.recurring_group_id = b.recurring_group_id)
              )
        """)).fetchall()

        for r in rows:
            # manter o de número menor, empurrar o de número maior
            num_a = r.num_a or r.rnum_a or 0
            num_b = r.num_b or r.rnum_b or 0
            id_to_move = r.id_b if num_b >= num_a else r.id_a

            exp = db.session.get(Expense, id_to_move)
            new_month, new_year = month_offset(exp.month, exp.year, 1)
            print(f"[grupo] '{r.description[:35]}' ID={id_to_move}: "
                  f"{exp.month:02d}/{exp.year} -> {new_month:02d}/{new_year}")
            exp.month = new_month
            exp.year  = new_year
            moved += 1

        # ── 2. Recorrente + Simples no mesmo mês ──────────────────────────
        rows2 = db.session.execute(text("""
            SELECT a.id AS id_recorrente, b.id AS id_simples,
                   a.month, a.year, a.description
            FROM expenses a
            JOIN expenses b
              ON  a.user_id               = b.user_id
              AND a.month                 = b.month
              AND a.year                  = b.year
              AND ROUND(a.amount, 2)      = ROUND(b.amount, 2)
              AND a.description           = b.description
              AND a.recurring_group_id IS NOT NULL
              AND b.recurring_group_id IS NULL
              AND b.installment_group_id IS NULL
        """)).fetchall()

        for r in rows2:
            exp = db.session.get(Expense, r.id_simples)
            new_month, new_year = month_offset(exp.month, exp.year, 1)
            print(f"[simples] '{r.description[:35]}' ID={r.id_simples}: "
                  f"{exp.month:02d}/{exp.year} -> {new_month:02d}/{new_year}")
            exp.month = new_month
            exp.year  = new_year
            moved += 1

        if moved:
            db.session.commit()
            print(f"\n✅ {moved} despesa(s) movidas para o mês seguinte.")
        else:
            print("Nenhuma duplicata encontrada.")


if __name__ == '__main__':
    fix()
