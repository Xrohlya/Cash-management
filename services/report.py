from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie

from database.db import get_connection
from database.repository import (
    financial_period_end,
    financial_period_start,
    get_financial_day,
    get_month,
    get_savings,
    normalize_expense_category,
)


BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "data" / "reports"
FONT_PATH = BASE_DIR / "assets" / "DejaVuSans.ttf"
FONT_NAME = "BudgetDejaVu"

if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def parse_report_period(user_id: int, value: str | None = None):
    """Return financial period dates from YYYY-MM or YYYY-MM-DD/20 input."""
    if not value:
        today = date.today()
        return financial_period_start(user_id, today), financial_period_end(user_id, today)

    value = value.strip()
    if len(value) == 7:
        start = datetime.strptime(value, "%Y-%m").date().replace(day=get_financial_day(user_id))
    else:
        start = datetime.strptime(value, "%Y-%m-%d").date()
        if start.day != get_financial_day(user_id):
            raise ValueError("Дата периода должна начинаться в выбранный день")

    if start.month == 12:
        end = date(start.year + 1, 1, start.day)
    else:
        end = date(start.year, start.month + 1, start.day)
    return start, end


def get_report_data(user_id: int, start: date, end: date):
    month = get_month(user_id, start.isoformat())
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT created_at, kind, amount, description FROM transactions "
            "WHERE user_id=? AND created_at>=? AND created_at<? ORDER BY created_at ASC, id ASC",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()

    expenses = [r for r in rows if r["kind"] == "expense"]
    incomes = [r for r in rows if r["kind"] == "income"]
    mandatory = [r for r in rows if r["kind"] == "mandatory"]
    rents = [r for r in rows if r["kind"] == "rent"]
    saved_rows = [r for r in rows if r["kind"] == "save"]

    category_totals = defaultdict(float)
    daily_totals = defaultdict(float)
    for row in expenses:
        amount = float(row["amount"])
        category_totals[normalize_expense_category(row["description"])] += amount
        day = datetime.fromisoformat(row["created_at"]).date()
        daily_totals[day] += amount

    days = []
    cursor = start
    while cursor < end:
        days.append((cursor, daily_totals.get(cursor, 0.0)))
        cursor += timedelta(days=1)

    return {
        "month": month,
        "rows": rows,
        "expenses": expenses,
        "incomes": incomes,
        "mandatory": mandatory,
        "rents": rents,
        "saved_rows": saved_rows,
        "category_totals": dict(sorted(category_totals.items(), key=lambda x: (-x[1], x[0].casefold()))),
        "daily_totals": days,
        "gross_income": sum(float(r["amount"]) for r in incomes),
        "mandatory_total": sum(float(r["amount"]) for r in mandatory),
        "rent_total": sum(float(r["amount"]) for r in rents),
        "saved_total": sum(float(r["amount"]) for r in saved_rows),
        "expense_total": sum(float(r["amount"]) for r in expenses),
        "savings_total": get_savings(user_id),
    }


def money(value):
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def _styles():
    return {
        "title": ParagraphStyle("title", fontName=FONT_NAME, fontSize=22, leading=26, alignment=TA_CENTER, spaceAfter=5),
        "subtitle": ParagraphStyle("subtitle", fontName=FONT_NAME, fontSize=10, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#666666"), spaceAfter=15),
        "h": ParagraphStyle("h", fontName=FONT_NAME, fontSize=13, leading=16, spaceBefore=8, spaceAfter=7),
        "body": ParagraphStyle("body", fontName=FONT_NAME, fontSize=8.5, leading=11),
        "small": ParagraphStyle("small", fontName=FONT_NAME, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#555555")),
        "right": ParagraphStyle("right", fontName=FONT_NAME, fontSize=8.5, leading=11, alignment=TA_RIGHT),
        "center": ParagraphStyle("center", fontName=FONT_NAME, fontSize=8.5, leading=11, alignment=TA_CENTER),
    }


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 7)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(18 * mm, 10 * mm, "Личный бюджет")
    canvas.drawRightString(192 * mm, 10 * mm, f"Страница {doc.page}")
    canvas.restoreState()


def _summary_table(data, styles):
    month = data["month"]
    budget = float(month["budget"])
    available = budget - float(month["spent"]) - float(month["rent"]) - float(month["saved"])
    net_income = data["gross_income"] - data["mandatory_total"]

    items = [
        ("Доход брутто", money(data["gross_income"])),
        ("Обязательный вычет", money(data["mandatory_total"])),
        ("Бюджет после вычета", money(net_income)),
        ("Обычные расходы", money(data["expense_total"])),
        ("Квартира", money(data["rent_total"])),
        ("Отложено в накопления", money(data["saved_total"])),
        ("Осталось доступно", money(available)),
        ("Накопления всего", money(data["savings_total"])),
    ]
    table_data = [[Paragraph("Показатель", styles["body"]), Paragraph("Сумма", styles["right"])]]
    for name, value in items:
        table_data.append([Paragraph(name, styles["body"]), Paragraph(f"<b>{value}</b>", styles["right"])])

    table = Table(table_data, colWidths=[112 * mm, 55 * mm], hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _category_chart(category_totals):
    data = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:8]
    if not data:
        return Paragraph("Расходов по категориям нет.", _styles()["small"])

    drawing = Drawing(500, 220)
    chart = VerticalBarChart()
    chart.x = 45
    chart.y = 35
    chart.height = 150
    chart.width = 430
    chart.data = [[v for _, v in data]]
    chart.categoryAxis.categoryNames = [k for k, _ in data]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueStep = max(1, round(max(v for _, v in data) / 4 / 1000) * 1000)
    chart.barWidth = 22
    chart.groupSpacing = 12
    chart.barSpacing = 4
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fontName = FONT_NAME
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 35
    chart.categoryAxis.labels.dy = -8
    chart.bars[0].fillColor = colors.HexColor("#374151")
    drawing.add(chart)
    return drawing


def _daily_chart(daily_totals):
    nonzero = [(d, v) for d, v in daily_totals if v > 0]
    if not nonzero:
        return Paragraph("Расходов по дням нет.", _styles()["small"])

    drawing = Drawing(500, 220)
    chart = VerticalBarChart()
    chart.x = 45
    chart.y = 35
    chart.height = 150
    chart.width = 430
    chart.data = [[v for _, v in daily_totals]]
    chart.categoryAxis.categoryNames = [d.strftime("%d.%m") for d, _ in daily_totals]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueStep = max(1, round(max(v for _, v in daily_totals) / 4 / 1000) * 1000)
    chart.barWidth = 8
    chart.groupSpacing = 5
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fontName = FONT_NAME
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.angle = 45
    chart.categoryAxis.labels.dy = -10
    chart.bars[0].fillColor = colors.HexColor("#6B7280")
    drawing.add(chart)
    return drawing


def build_monthly_report(user_id: int, start: date, end: date) -> Path:
    data = get_report_data(user_id, start, end)
    styles = _styles()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = REPORT_DIR / f"budget_{user_id}_{start.isoformat()}_{(end - timedelta(days=1)).isoformat()}.pdf"

    doc = BaseDocTemplate(
        str(filename), pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=15 * mm, bottomMargin=17 * mm,
        title=f"Отчёт по бюджету {start:%d.%m.%Y} — {(end - timedelta(days=1)):%d.%m.%Y}",
        author="Личный бюджет",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="budget", frames=frame, onPage=_header_footer)])

    story = [
        Paragraph("ОТЧЁТ ПО ЛИЧНОМУ БЮДЖЕТУ", styles["title"]),
        Paragraph(f"Финансовый месяц: <b>{start:%d.%m.%Y} — {(end - timedelta(days=1)):%d.%m.%Y}</b>", styles["subtitle"]),
        _summary_table(data, styles),
        Spacer(1, 8 * mm),
        Paragraph("📊 Расходы по категориям", styles["h"]),
        _category_chart(data["category_totals"]),
        Spacer(1, 5 * mm),
        Paragraph("📅 Расходы по дням", styles["h"]),
        _daily_chart(data["daily_totals"]),
    ]

    category_rows = [[Paragraph("Категория", styles["body"]), Paragraph("Сумма", styles["right"])]]
    for category, amount in data["category_totals"].items():
        category_rows.append([Paragraph(category, styles["body"]), Paragraph(money(amount), styles["right"])])
    if len(category_rows) > 1:
        cat_table = Table(category_rows, colWidths=[112 * mm, 55 * mm], hAlign="CENTER", repeatRows=1)
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story += [Paragraph("Категории", styles["h"]), cat_table]

    daily_rows = [[
        Paragraph("Дата", styles["body"]),
        Paragraph("Расходы", styles["right"]),
    ]]
    for day, amount in data["daily_totals"]:
        daily_rows.append([Paragraph(day.strftime("%d.%m.%Y"), styles["body"]), Paragraph(money(amount), styles["right"])])
    daily_table = Table(daily_rows, colWidths=[112 * mm, 55 * mm], hAlign="CENTER", repeatRows=1)
    daily_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [Paragraph("Детализация по дням", styles["h"]), daily_table]

    transaction_rows = [[
        Paragraph("Дата / время", styles["body"]),
        Paragraph("Категория", styles["body"]),
        Paragraph("Сумма", styles["right"]),
    ]]
    for row in data["expenses"]:
        dt = datetime.fromisoformat(row["created_at"])
        transaction_rows.append([
            Paragraph(dt.strftime("%d.%m.%Y %H:%M"), styles["small"]),
            Paragraph(row["description"], styles["body"]),
            Paragraph(money(float(row["amount"])), styles["right"]),
        ])
    if len(transaction_rows) > 1:
        tx_table = Table(transaction_rows, colWidths=[45 * mm, 77 * mm, 45 * mm], hAlign="CENTER", repeatRows=1)
        tx_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story += [Paragraph("Все расходы", styles["h"]), tx_table]

    story += [Spacer(1, 6 * mm), Paragraph("Отчёт сформирован автоматически из истории операций бота.", styles["small"])]
    doc.build(story)
    return filename
