import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { dailyData, dailyOption, categoriesOption } from "../webapp/static/modules/chart-options.js";

const analytics = { period_start: "2026-10-20", period_end: "2026-11-19", as_of: "2026-10-31",
  daily: [{ date: "2026-10-19", amount: 9000 }, { date: "2026-10-22", amount: 500 },
          { date: "2026-10-31", amount: -250 }, { date: "2026-11-01", amount: 600 }] };

test("daily chart fills zeros within the financial period, never future or previous days", () => {
  const all = dailyData(analytics, 0);
  assert.equal(all.length, 12);
  assert.equal(all[0].date, "2026-10-20");
  assert.equal(all[0].amount, 0);
  assert.equal(all.at(-1).amount, -250);
  assert.equal(dailyData(analytics, 7).length, 7);
  assert.deepEqual(dailyData({ ...analytics, as_of: "2026-10-01" }), []);
});

test("chart options retain refund signs and disable motion when requested", () => {
  const daily = dailyOption(dailyData(analytics), true);
  assert.equal(daily.animation, false);
  assert.equal(daily.series[0].data.at(-1).value, -250);
  assert.equal(daily.tooltip.renderMode, "richText");
  const categories = categoriesOption([{ name: "Еда", amount: 1000 }, { name: "Разное", amount: -400 }]);
  assert.equal(categories.series[0].data[1].value, -400);
  assert.deepEqual(categories.yAxis.data, ["Еда", "Разное"]);
});

test("vendored ECharts renders both charts at mobile and desktop widths", () => {
  const require = createRequire(import.meta.url);
  const echarts = require("../webapp/static/vendor/echarts/echarts-6.0.0.min.js");
  for (const width of [320, 390, 1100]) {
    const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width, height: 300 });
    try {
      for (const option of [dailyOption(dailyData(analytics), true), categoriesOption([{ name: "Еда", amount: 1000 }, { name: "Возврат", amount: -400 }], true)]) {
        chart.setOption(option, { notMerge: true });
        const svg = chart.renderToSVGString();
        assert.match(svg, /<path/);
        assert.doesNotMatch(svg, /NaN/);
      }
    } finally { chart.dispose(); }
  }
});
