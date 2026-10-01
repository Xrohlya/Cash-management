import { telegram, operationLabels, operation, showToast } from "./core.js?v=20261001-3";

function initReceiptActions() {
  function loadReceiptOcr() {
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
      script.onload = () => resolve(window.Tesseract);
      script.onerror = () => reject(new Error("Не удалось загрузить распознавание чека"));
      document.head.append(script);
    });
  }

  function receiptAmount(text) {
    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const amountPattern = /(?:\d{1,3}(?:[\s.]\d{3})*|\d+)(?:[,.]\d{2})?/g;
    const decimalPattern = /(?:\d{1,3}(?:[\s.]\d{3})*|\d+)[,.]\d{2}/g;
    const values = (linesToRead, pattern) => linesToRead.flatMap((line) =>
      (line.match(pattern) || []).map((value) => Number(value.replace(/[\s.](?=\d{3})/g, "").replace(",", ".")))
    ).filter((value) => Number.isFinite(value) && value > 0 && value < 1_000_000);
    const preferred = lines.filter((line) => /итого|к оплате|сумма|total|оплачено/i.test(line));
    const totals = values(preferred, amountPattern);
    if (totals.length) return Math.max(...totals);
    const candidates = values(lines.filter((line) => !/инн|кассир|чек|дата|смена/i.test(line)), decimalPattern);
    return candidates.length ? Math.max(...candidates) : null;
  }

  function receiptCategory(text) {
    const value = text.toLocaleLowerCase("ru-RU");
    const groups = [
      ["Еда", ["продукт", "пятероч", "перекрест", "вкусвилл", "магнит", "лента", "ашан", "молоко", "хлеб", "кофе", "кафе", "ресторан"]],
      ["Транспорт", ["такси", "бензин", "топливо", "парков", "метро", "автобус"]],
      ["Здоровье", ["аптек", "лекар", "клиник", "медицин"]],
      ["Дом и связь", ["интернет", "мобильн", "телефон", "хозтовар", "ремонт"]],
      ["Подписки", ["подписк", "онлайн-сервис", "subscription"]],
      ["Одежда", ["одежд", "обув", "fashion"]],
    ];
    return groups.find(([, words]) => words.some((word) => value.includes(word)))?.[0] || "Разное";
  }

  document.getElementById("scan-receipt").addEventListener("click", () => {
    document.getElementById("receipt-photo").click();
  });

  document.getElementById("receipt-photo").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const status = document.getElementById("receipt-status");
    const button = document.getElementById("scan-receipt");
    button.disabled = true;
    status.textContent = "Подготавливаю распознавание…";
    try {
      const tesseract = await loadReceiptOcr();
      const result = await tesseract.recognize(file, "rus+eng", {
        logger: (progress) => {
          if (progress.status === "recognizing text") {
            status.textContent = `Читаю чек: ${Math.round(progress.progress * 100)}%`;
          }
        },
      });
      const text = result.data?.text || "";
      const amount = receiptAmount(text);
      if (!amount) throw new Error("Не удалось найти итоговую сумму. Введите её вручную.");
      operation.kind = "expense";
      document.querySelectorAll("#operation-kind button").forEach((item) => item.classList.toggle("active", item.dataset.kind === "expense"));
      document.getElementById("submit").textContent = operationLabels.expense[0];
      document.getElementById("amount").value = amount.toFixed(2);
      document.getElementById("description").value = receiptCategory(text);
      status.textContent = "Чек распознан. Проверьте сумму перед записью.";
      telegram?.HapticFeedback?.notificationOccurred?.("success");
    } catch (error) {
      status.textContent = error.message;
      showToast(error.message);
    } finally {
      button.disabled = false;
      event.target.value = "";
    }
  });
}

export { initReceiptActions };
