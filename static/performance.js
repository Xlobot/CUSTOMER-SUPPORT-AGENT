/**
 * static/performance.js — NetCare AI
 * Renders Model Performance Dashboard analytics, loss curves, confusion matrix, and agent evaluations.
 */

let lossChartInstance = null;
let accuracyChartInstance = null;

async function loadPerformanceData() {
  try {
    const res = await fetch("/api/model/performance");
    if (!res.ok) throw new Error("Failed to fetch performance data");
    const data = await res.json();

    renderKPIs(data);
    renderLossChart(data.training_history);
    renderAccuracyChart(data.training_history);
    renderConfusionMatrix(data.model_metrics);
    renderAgentEvaluations(data.agent_evaluations);
    renderDatasetStats(data.preprocessing_report);
  } catch (err) {
    console.error("Error loading performance data:", err);
  }
}

function renderKPIs(data) {
  const m = data.model_metrics || {};
  const h = data.training_history || {};

  document.getElementById("metric-accuracy").textContent = m.test_accuracy != null ? `${m.test_accuracy}%` : "Not available";
  document.getElementById("metric-f1").textContent = m.macro_f1 != null ? m.macro_f1.toFixed(4) : "Not available";

  const prec = m.macro_precision != null ? m.macro_precision.toFixed(2) : "—";
  const rec = m.macro_recall != null ? m.macro_recall.toFixed(2) : "—";
  document.getElementById("metric-precision-recall").textContent = `${prec} / ${rec}`;

  if (m.target_met) {
    document.getElementById("target-status").innerHTML = `<span style="color:var(--positive);font-weight:600;">Target Exceeded (${m.test_accuracy}% ≥ 95.5%)</span>`;
  } else {
    document.getElementById("target-status").innerHTML = `<span style="color:var(--warning);font-weight:500;">In Progress (${m.test_accuracy}% < 95.5%)</span>`;
  }

  if (m.foundation_architecture) {
    document.getElementById("metric-model").textContent = m.foundation_architecture;
  }
  if (h.epochs) {
    document.getElementById("metric-epochs").textContent = `${h.epochs} Epochs • Best Val Acc: ${h.best_val_acc}%`;
  }
}

function renderLossChart(historyData) {
  const ctx = document.getElementById("lossChart");
  if (!ctx || !historyData || !historyData.history) return;

  const labels = historyData.history.map(item => `Epoch ${item.epoch}`);
  const trainLoss = historyData.history.map(item => item.train_loss);
  const valLoss = historyData.history.map(item => item.val_loss);

  if (lossChartInstance) lossChartInstance.destroy();

  lossChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Training Loss",
          data: trainLoss,
          borderColor: "#2563EB",
          backgroundColor: "rgba(37, 99, 235, 0.1)",
          tension: 0.3,
          fill: true
        },
        {
          label: "Validation Loss",
          data: valLoss,
          borderColor: "#EF4444",
          borderDash: [5, 5],
          tension: 0.3,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" }
      },
      scales: {
        y: { beginAtZero: false, title: { display: true, text: "Log Loss" } }
      }
    }
  });
}

function renderAccuracyChart(historyData) {
  const ctx = document.getElementById("accuracyChart");
  if (!ctx || !historyData || !historyData.history) return;

  const labels = historyData.history.map(item => `Epoch ${item.epoch}`);
  const valAcc = historyData.history.map(item => item.val_accuracy);
  const macroF1 = historyData.history.map(item => item.macro_f1 * 100);

  if (accuracyChartInstance) accuracyChartInstance.destroy();

  accuracyChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Validation Accuracy (%)",
          data: valAcc,
          borderColor: "#10B981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          tension: 0.3,
          fill: true
        },
        {
          label: "Macro F1 (%)",
          data: macroF1,
          borderColor: "#8B5CF6",
          tension: 0.3,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" }
      },
      scales: {
        y: { min: 80, max: 100, title: { display: true, text: "Score (%)" } }
      }
    }
  });
}

function renderConfusionMatrix(metrics) {
  const table = document.getElementById("confusion-matrix-table");
  if (!table || !metrics || !metrics.classes || !metrics.confusion_matrix) {
    if (table) table.innerHTML = "<tr><td>Confusion matrix data not available.</td></tr>";
    return;
  }

  const classes = metrics.classes;
  const cm = metrics.confusion_matrix;

  let html = "<thead><tr><th style='padding:8px;border:1px solid #E2E8F0;background:#F8FAFC;'>True \\ Pred</th>";
  classes.forEach(c => {
    const shortName = c.replace(/_/g, " ").substring(0, 10);
    html += `<th style='padding:8px;border:1px solid #E2E8F0;background:#F8FAFC;' title='${c}'>${shortName}</th>`;
  });
  html += "</tr></thead><tbody>";

  cm.forEach((row, rIdx) => {
    html += `<tr><th style='padding:8px;border:1px solid #E2E8F0;background:#F8FAFC;text-align:left;'>${classes[rIdx].replace(/_/g, " ")}</th>`;
    row.forEach((val, cIdx) => {
      const isDiag = (rIdx === cIdx);
      const bg = isDiag && val > 0 ? "background:#ECFDF5;color:#047857;font-weight:700;" : (val > 0 ? "background:#FEF2F2;color:#B91C1C;" : "color:#94A3B8;");
      html += `<td style='padding:8px;border:1px solid #E2E8F0;text-align:center;${bg}'>${val}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody>";

  table.innerHTML = html;
}

function renderAgentEvaluations(evals) {
  const container = document.getElementById("agent-eval-grid");
  if (!container || !evals) return;

  const agentKeys = Object.keys(evals);
  let html = "";

  agentKeys.forEach(k => {
    const agent = evals[k];
    const metrics = agent.metrics || {};
    let metricsHtml = "";
    Object.keys(metrics).forEach(mName => {
      const val = metrics[mName];
      metricsHtml += `
        <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #F1F5F9;font-size:12px;">
          <span style="color:#64748B;">${mName.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}:</span>
          <span style="font-weight:600;color:#0F172A;">${typeof val === 'number' ? val + '%' : val}</span>
        </div>
      `;
    });

    html += `
      <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <h4 style="margin:0;font-size:14px;font-weight:700;color:#0F172A;">${agent.name}</h4>
          <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:#10B981;color:#fff;font-weight:700;">${agent.status || 'PASS'}</span>
        </div>
        <p style="font-size:11px;color:#64748B;margin:0 0 12px 0;">${agent.role}</p>
        <div style="margin-bottom:12px;">${metricsHtml}</div>
        <p style="font-size:11px;color:#475569;margin:0;font-style:italic;">"${agent.eval_summary || ''}"</p>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderDatasetStats(report) {
  if (!report) return;
  if (report.sft_samples && report.sft_samples.total) {
    const el = document.getElementById("stat-sft-total");
    if (el) el.textContent = report.sft_samples.total;
  }
  if (report.classification_samples && report.classification_samples.total) {
    const el = document.getElementById("stat-cls-total");
    if (el) el.textContent = report.classification_samples.total;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadPerformanceData();
});
