import flet as ft
from datetime import datetime
import requests
import threading

# --- הגדרות ענן (מלא את הפרטים מהאתר של Supabase) ---
SUPABASE_URL = "https://okskvkucyieireegxzsv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9rc2t2a3VjeWllaXJlZWd4enN2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5MjA2NDcsImV4cCI6MjA4MjQ5NjY0N30.-Twtx2XWRl2IhAv2g-Ch1IaJs85mZjmSzfTwiLwZyRY"

try:
    from flet_charts import PieChart, PieChartSection
except ImportError:
    PieChart = None
    PieChartSection = None

class CloudSync:
    def __init__(self):
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.expenses_url = f"{SUPABASE_URL}/rest/v1/expenses"
        self.budgets_url = f"{SUPABASE_URL}/rest/v1/budgets"

    def load_data(self):
        try:
            exp_r = requests.get(self.expenses_url, headers=self.headers)
            bud_r = requests.get(self.budgets_url, headers=self.headers)
            expenses = exp_r.json() if exp_r.status_code == 200 else []
            budgets_list = bud_r.json() if bud_r.status_code == 200 else []
            monthly_budgets = {b['month_key']: float(b['amount']) for b in budgets_list}
            return {"monthly_budgets": monthly_budgets, "expenses": expenses}
        except:
            return {"monthly_budgets": {}, "expenses": []}

    def save_expense(self, ex):
        requests.post(self.expenses_url, headers=self.headers, json=ex)

    def delete_expense(self, ex_id):
        requests.delete(f"{self.expenses_url}?id=eq.{ex_id}", headers=self.headers)

    def save_budget(self, month, amount):
        payload = {"month_key": month, "amount": amount}
        headers = self.headers.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        requests.post(self.budgets_url, headers=headers, json=payload)

def main(page: ft.Page):
    page.title = "ניהול תקציב משפחתי"
    page.rtl = True
    page.theme_mode = "light"
    page.window_width = 450
    page.scroll = "auto"

    sync = CloudSync()
    data_store = sync.load_data()
    categories = ["אוכל", "בגדים והנעלה", "בזבוזים", "בית קפה", "פארם", "שונות"]
    chart_colors = ["blue", "red", "green", "orange", "purple", "cyan"]
    
    txt_balance = ft.Text("יתרה: 0 ₪", size=24, weight="bold")
    txt_spent = ft.Text("הוצאות: 0 ₪", size=16, color="red")
    error_message = ft.Text("", color="red", size=12, visible=False)
    
    def validate_amount(e):
        val = input_amount.value
        if not val:
            input_amount.error_text = None
            error_message.visible = False
            btn_save.disabled = False
        else:
            is_numeric = val.replace('.', '', 1).isdigit()
            if is_numeric:
                input_amount.error_text = None
                error_message.visible = False
                btn_save.disabled = False
            else:
                input_amount.error_text = "שגיאה"
                error_message.value = "ניתן להכניס ספרות בלבד!"
                error_message.visible = True
                btn_save.disabled = True
        page.update()

    input_amount = ft.TextField(label="סכום (₪)", keyboard_type="number", on_change=validate_amount)
    input_budget = ft.TextField(label="תקציב לחודש", value="2000", width=120, keyboard_type="number")
    dropdown_cat = ft.Dropdown(label="קטגוריה", options=[ft.dropdown.Option(c) for c in categories], value=categories[0])
    input_desc = ft.TextField(label="תיאור ההוצאה")
    current_month = datetime.now().strftime("%Y-%m")
    month_picker = ft.Dropdown(label="חודש", width=150, options=[ft.dropdown.Option(current_month)], value=current_month)
    chart = PieChart(sections=[], height=250) if PieChart else ft.Text("הגרף יופיע כאן")
    expenses_list = ft.Column(spacing=10)
    btn_save = ft.FilledButton("שמור בענן", on_click=lambda e: add_expense(e), width=400)

    def update_ui(e=None):
        nonlocal data_store
        sel_month = month_picker.value
        
        if e and e.control == input_budget:
            try:
                amt = float(input_budget.value or 0)
                data_store["monthly_budgets"][sel_month] = amt
                sync.save_budget(sel_month, amt)
            except: pass

        budget = data_store["monthly_budgets"].get(sel_month, 2000.0)
        input_budget.value = str(int(budget))
        
        relevant_expenses = [ex for ex in data_store["expenses"] if ex.get("month_key") == sel_month]
        total_spent = sum(float(ex['amount']) for ex in relevant_expenses)
        balance = budget - total_spent

        txt_spent.value = f"הוצאות: {int(total_spent)} ₪"
        txt_balance.value = f"יתרה: {int(balance)} ₪"
        txt_balance.color = "green" if balance >= 0 else "red"

        if PieChart and total_spent > 0:
            cat_totals = {c: 0 for c in categories}
            for ex in relevant_expenses:
                cat_totals[ex['category']] = cat_totals.get(ex['category'], 0) + float(ex['amount'])
            
            chart.sections = [
                PieChartSection(
                    val, 
                    title=f"{cat}\n{((val/total_spent)*100):.1f}%", 
                    color=chart_colors[i%6], 
                    radius=60,
                    title_style=ft.TextStyle(size=10, weight="bold", color="white")
                )
                for i, (cat, val) in enumerate(cat_totals.items()) if val > 0
            ]
        elif PieChart:
            chart.sections = []

        expenses_list.controls = []
        for ex in reversed(relevant_expenses):
            display_date = ex.get("date", "").split(" ")[0] if ex.get("date") else ""
            expenses_list.controls.append(
                ft.ListTile(
                    leading=ft.Text(display_date, size=12),
                    title=ft.Text(f"{ex['category']}: {ex['amount']} ₪"),
                    subtitle=ft.Text(ex.get("description") or ex.get("desc") or "-"),
                    trailing=ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color="red", 
                        on_click=lambda _, id=ex["id"]: delete_expense(id)
                    )
                )
            )
        page.update()

    def add_expense(e):
        if not input_amount.value or btn_save.disabled: return
        
        now = datetime.now()
        amt = float(input_amount.value)
        cat = dropdown_cat.value
        desc = input_desc.value or "-"
        date_str = now.strftime("%d/%m %H:%M")
        month_k = now.strftime("%Y-%m")

        # 1. עדכון אופטימי (מקומי)
        new_ex = {"id": f"temp_{now.timestamp()}", "amount": amt, "category": cat, "description": desc, "date": date_str, "month_key": month_k}
        data_store["expenses"].append(new_ex)
        
        input_amount.value = ""
        input_desc.value = ""
        update_ui()

        # 2. סנכרון ברקע בעזרת Thread (במקום run_task)
        def sync_task():
            try:
                sync.save_expense({"amount": amt, "category": cat, "description": desc, "date": date_str, "month_key": month_k})
                refresh_data()
            except: pass
        
        threading.Thread(target=sync_task).start()

    def delete_expense(expense_id):
        # 1. עדכון אופטימי
        nonlocal data_store
        data_store["expenses"] = [ex for ex in data_store["expenses"] if ex["id"] != expense_id]
        update_ui()
        
        # 2. סנכרון ברקע
        def sync_task():
            try:
                sync.delete_expense(expense_id)
                refresh_data()
            except: pass
            
        threading.Thread(target=sync_task).start()

    def refresh_data(e=None):
        nonlocal data_store
        data_store = sync.load_data()
        update_ui()

    month_picker.on_change = update_ui
    input_budget.on_change = update_ui

    page.add(
        ft.Column(
            horizontal_alignment="center",
            controls=[
                ft.Text("תקציב משפחתי", size=28, weight="bold"),
                ft.Row([month_picker, input_budget], alignment="spaceBetween"),
                ft.Divider(),
                txt_balance, 
                txt_spent,
                ft.Divider(),
                ft.Text("הזנה:", weight="bold", size=18),
                input_amount,
                error_message,
                dropdown_cat,
                input_desc,
                btn_save,
                ft.Divider(),
                ft.Text("היסטוריה:", weight="bold", size=18),
                expenses_list,
                ft.Divider(),
                ft.Text("סיכום גרפי:", weight="bold", size=18),
                ft.Container(content=chart, padding=20),
                ft.FilledButton("רענן נתונים", icon=ft.Icons.REFRESH, on_click=refresh_data, width=400),
            ]
        )
    )
    refresh_data()

if __name__ == "__main__":
    ft.run(main)