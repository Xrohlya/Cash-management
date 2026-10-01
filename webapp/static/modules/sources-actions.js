import { api, showToast } from "./core.js?v=20261001-1";
import { renderSources, renderSourcesOverview } from "./sources.js?v=20261001-1";

function initSourcesActions() {
  function resetSourceForm() {
    document.getElementById("source-form").reset();
    document.getElementById("source-id").value = "";
    document.getElementById("save-source").textContent = "Добавить источник";
    document.getElementById("cancel-source").hidden = true;
  }

  document.getElementById("source-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const id = document.getElementById("source-id").value;
    const button = document.getElementById("save-source");
    button.disabled = true;
    try {
      const items = await api(`/api/income-sources${id ? `/${id}` : ""}`, {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("source-name").value.trim(),
          withholding_percent: Number(document.getElementById("source-percent").value),
        }),
      });
      renderSources(items);
      renderSourcesOverview(items);
      resetSourceForm();
      showToast(id ? "Источник обновлён" : "Источник добавлен");
    } catch (error) {
      showToast(error.message);
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("cancel-source").addEventListener("click", resetSourceForm);

  document.getElementById("sources-list").addEventListener("click", async (event) => {
    const edit = event.target.closest("[data-source-edit]");
    if (edit) {
      document.getElementById("source-id").value = edit.dataset.sourceEdit;
      document.getElementById("source-name").value = edit.dataset.sourceName;
      document.getElementById("source-percent").value = edit.dataset.sourcePercent;
      document.getElementById("save-source").textContent = "Сохранить";
      document.getElementById("cancel-source").hidden = false;
      document.getElementById("source-name").focus();
      return;
    }
    const remove = event.target.closest("[data-source-delete]");
    if (!remove || !window.confirm("Удалить источник дохода? История останется сохранена.")) return;
    try {
      const items = await api(`/api/income-sources/${remove.dataset.sourceDelete}/delete`, { method: "POST" });
      renderSources(items);
      renderSourcesOverview(items);
      showToast("Источник удалён");
    } catch (error) {
      showToast(error.message);
    }
  });
}

export { initSourcesActions };
