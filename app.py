#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(
    os.getenv(
        "ADS_TRACKER_DATA_DIR",
        os.getenv("RAILWAY_VOLUME_MOUNT_PATH", str(APP_DIR / "data")),
    )
)
DB_PATH = DATA_DIR / "ads_tracker.db"
HOST = os.getenv("ADS_TRACKER_HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", os.getenv("ADS_TRACKER_PORT", "8765")))


HTML_PAGE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Планировщик рекламы</title>
  <style>
    :root {
      --bg: #f3f1ea;
      --panel: rgba(255, 252, 245, 0.92);
      --ink: #1f2a24;
      --muted: #5d6962;
      --line: rgba(59, 77, 67, 0.14);
      --accent: #2e6d5c;
      --accent-soft: rgba(46, 109, 92, 0.1);
      --danger: #a84545;
      --danger-soft: #f7e1dc;
      --warn: #9b6a1d;
      --warn-soft: #f6ead4;
      --ok: #2b6a4f;
      --ok-soft: #deefe6;
      --shadow: 0 18px 40px rgba(35, 47, 40, 0.08);
      --radius: 18px;
      --radius-sm: 12px;
      --font: "Avenir Next", "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: var(--font);
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(205, 228, 216, 0.85), transparent 28%),
        radial-gradient(circle at bottom left, rgba(247, 228, 204, 0.82), transparent 22%),
        var(--bg);
    }

    a { color: inherit; }

    .shell {
      max-width: 1380px;
      margin: 0 auto;
      padding: 28px 20px 56px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }

    .hero-main {
      padding: 28px;
      position: relative;
      overflow: hidden;
    }

    .hero-main::after {
      content: "";
      position: absolute;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      right: -70px;
      top: -80px;
      background: rgba(46, 109, 92, 0.12);
    }

    .eyebrow {
      display: inline-flex;
      padding: 8px 14px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    h1 {
      margin: 16px 0 10px;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1.02;
      letter-spacing: -0.03em;
    }

    .hero-text {
      margin: 0;
      max-width: 760px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.6;
    }

    .hero-side {
      padding: 24px;
      display: grid;
      gap: 16px;
      align-content: start;
    }

    .year-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
      flex-wrap: wrap;
    }

    .year-row p {
      margin: 0 0 6px;
      color: var(--muted);
    }

    select, input, textarea, button {
      font: inherit;
    }

    select, input, textarea {
      width: 100%;
      border: 1px solid rgba(59, 77, 67, 0.18);
      background: rgba(255, 255, 255, 0.72);
      border-radius: 12px;
      padding: 12px 14px;
      color: var(--ink);
      transition: border-color .18s ease, box-shadow .18s ease;
    }

    select:focus, input:focus, textarea:focus {
      outline: none;
      border-color: rgba(46, 109, 92, 0.45);
      box-shadow: 0 0 0 4px rgba(46, 109, 92, 0.12);
    }

    textarea {
      resize: vertical;
      min-height: 96px;
    }

    button {
      border: 0;
      border-radius: 12px;
      padding: 12px 16px;
      cursor: pointer;
      transition: transform .18s ease, opacity .18s ease;
    }

    button:hover { transform: translateY(-1px); }
    button:active { transform: translateY(0); }

    .btn-primary {
      background: linear-gradient(135deg, #2e6d5c, #4a8676);
      color: white;
      box-shadow: 0 12px 24px rgba(46, 109, 92, 0.18);
    }

    .btn-secondary {
      background: rgba(46, 109, 92, 0.1);
      color: var(--accent);
    }

    .btn-ghost {
      background: rgba(31, 42, 36, 0.06);
      color: var(--ink);
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }

    .stat-card {
      padding: 18px;
      min-height: 118px;
    }

    .stat-label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: clamp(24px, 3vw, 34px);
      font-weight: 700;
      letter-spacing: -0.03em;
    }

    .stat-note {
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }

    .layout {
      display: grid;
      grid-template-columns: 1.15fr .85fr;
      gap: 18px;
      align-items: start;
    }

    .stack {
      display: grid;
      gap: 18px;
    }

    .section {
      padding: 22px;
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    .section-title {
      margin: 0;
      font-size: 24px;
      letter-spacing: -0.02em;
    }

    .section-subtitle {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
    }

    .agenda {
      display: grid;
      gap: 12px;
    }

    .agenda-card {
      border: 1px solid var(--line);
      border-radius: var(--radius-sm);
      padding: 16px;
      background: rgba(255, 255, 255, 0.72);
      display: grid;
      gap: 12px;
    }

    .agenda-card[data-tone="danger"] {
      background: var(--danger-soft);
      border-color: rgba(168, 69, 69, 0.18);
    }

    .agenda-card[data-tone="warn"] {
      background: var(--warn-soft);
      border-color: rgba(155, 106, 29, 0.18);
    }

    .agenda-card[data-tone="ok"] {
      background: var(--ok-soft);
      border-color: rgba(43, 106, 79, 0.18);
    }

    .agenda-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      flex-wrap: wrap;
    }

    .agenda-title {
      margin: 0;
      font-size: 18px;
    }

    .meta {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 13px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      padding: 7px 11px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }

    .tone-danger { background: rgba(168, 69, 69, 0.14); color: #853434; }
    .tone-warn { background: rgba(155, 106, 29, 0.14); color: #7f5614; }
    .tone-ok { background: rgba(43, 106, 79, 0.14); color: #20563e; }

    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    .inline-date {
      width: 170px;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .field {
      display: grid;
      gap: 8px;
    }

    .field-wide {
      grid-column: 1 / -1;
    }

    label {
      font-size: 13px;
      font-weight: 600;
      color: var(--muted);
    }

    .empty {
      padding: 22px;
      border-radius: 14px;
      border: 1px dashed rgba(59, 77, 67, 0.2);
      color: var(--muted);
      text-align: center;
      background: rgba(255, 255, 255, 0.46);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }

    th, td {
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }

    th {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .muted { color: var(--muted); }

    .inline-link {
      color: var(--accent);
      text-decoration: none;
    }

    .inline-link:hover { text-decoration: underline; }

    .flash {
      padding: 14px 16px;
      border-radius: 12px;
      display: none;
    }

    .flash.show { display: block; }
    .flash.ok { background: var(--ok-soft); color: #20563e; }
    .flash.error { background: var(--danger-soft); color: #853434; }

    @media (max-width: 1100px) {
      .hero, .layout { grid-template-columns: 1fr; }
      .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 760px) {
      .stats { grid-template-columns: 1fr; }
      .form-grid { grid-template-columns: 1fr; }
      .shell { padding: 16px 14px 42px; }
      .section, .hero-main, .hero-side, .stat-card { padding: 18px; }
      .actions { align-items: stretch; }
      .inline-date { width: 100%; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="panel hero-main">
        <div class="eyebrow">Регулярные посты</div>
        <h1>Список того, что нужно выложить сейчас, а не бесконечная таблица.</h1>
        <p class="hero-text">
          Для каждой площадки задается период, правило публикаций и дата
          <strong>«размещено до»</strong>. Приложение само показывает,
          где уже отстаем, где нужно публиковать сегодня и до какого числа план закрыт.
        </p>
      </div>
      <div class="panel hero-side">
        <div class="year-row">
          <div>
            <p>Рабочая дата</p>
            <strong id="todayLabel">...</strong>
          </div>
          <div style="min-width: 160px;">
            <label for="yearSelect">Год</label>
            <select id="yearSelect"></select>
          </div>
        </div>
        <div id="flash" class="flash"></div>
      </div>
    </section>

    <section class="stats" id="stats"></section>

    <section class="layout">
      <div class="stack">
        <section class="panel section">
          <div class="section-head">
            <div>
              <h2 class="section-title">Актуально сейчас</h2>
              <p class="section-subtitle">Какие каналы требуют выкладки в ближайшие дни.</p>
            </div>
          </div>
          <div id="agenda" class="agenda"></div>
        </section>

        <section class="panel section">
          <div class="section-head">
            <div>
              <h2 class="section-title">Все графики</h2>
              <p class="section-subtitle">Все активные кампании на выбранный год.</p>
            </div>
          </div>
          <div id="campaignsTable"></div>
        </section>
      </div>

      <div class="stack">
        <section class="panel section">
          <div class="section-head">
            <div>
              <h2 class="section-title">Новая площадка</h2>
              <p class="section-subtitle">Площадка добавляется один раз.</p>
            </div>
          </div>
          <form id="outletForm" class="form-grid">
            <div class="field">
              <label for="platform">Площадка</label>
              <select id="platform" name="platform" required>
                <option value="Telegram">Telegram</option>
                <option value="VK">VK</option>
                <option value="Max">Max</option>
                <option value="Другое">Другое</option>
              </select>
            </div>
            <div class="field">
              <label for="name">Название группы/канала</label>
              <input id="name" name="name" required placeholder="Например, Жильё в Абхазии">
            </div>
            <div class="field field-wide">
              <label for="link">Ссылка</label>
              <input id="link" name="link" placeholder="https://...">
            </div>
            <div class="field">
              <label for="adFormat">Формат</label>
              <input id="adFormat" name="ad_format" placeholder="Посты в группе">
            </div>
            <div class="field">
              <label for="managerName">Администратор</label>
              <input id="managerName" name="manager_name" placeholder="Мария Левина">
            </div>
            <div class="field field-wide">
              <label for="managerLink">Ссылка администратора</label>
              <input id="managerLink" name="manager_link" placeholder="https://...">
            </div>
            <div class="field field-wide">
              <label for="outletNotes">Комментарий</label>
              <textarea id="outletNotes" name="notes" placeholder="Любые заметки по площадке"></textarea>
            </div>
            <div class="field field-wide">
              <button class="btn-primary" type="submit">Сохранить площадку</button>
            </div>
          </form>
        </section>

        <section class="panel section">
          <div class="section-head">
            <div>
              <h2 class="section-title">Новый график</h2>
              <p class="section-subtitle">Для регулярных публикаций по площадке.</p>
            </div>
          </div>
          <form id="campaignForm" class="form-grid">
            <div class="field field-wide">
              <label for="outletId">Площадка</label>
              <select id="outletId" name="outlet_id" required></select>
            </div>
            <div class="field">
              <label for="campaignYear">Год</label>
              <input id="campaignYear" name="year" type="number" min="2024" step="1" required>
            </div>
            <div class="field">
              <label for="postingMode">Режим публикации</label>
              <select id="postingMode" name="posting_mode" required>
                <option value="daily_month_cap">Ежедневно, но с лимитом в месяц</option>
                <option value="daily_full">Ежедневно без пропусков</option>
              </select>
            </div>
            <div class="field">
              <label for="postsPerMonth">Постов в месяц</label>
              <input id="postsPerMonth" name="posts_per_month" type="number" min="1" step="1" value="30" required>
            </div>
            <div class="field">
              <label for="paidUntil">Оплачено до</label>
              <input id="paidUntil" name="paid_until" type="date">
            </div>
            <div class="field">
              <label for="startDate">Начало периода</label>
              <input id="startDate" name="start_date" type="date" required>
            </div>
            <div class="field">
              <label for="endDate">Конец периода</label>
              <input id="endDate" name="end_date" type="date" required>
            </div>
            <div class="field">
              <label for="paidStatus">Оплата</label>
              <select id="paidStatus" name="paid_status" required>
                <option value="оплачено">оплачено</option>
                <option value="не оплачено">не оплачено</option>
                <option value="частично">частично</option>
              </select>
            </div>
            <div class="field">
              <label for="placedUntil">Размещено до</label>
              <input id="placedUntil" name="placed_until" type="date">
            </div>
            <div class="field field-wide">
              <label for="campaignComment">Комментарий</label>
              <textarea id="campaignComment" name="comment" placeholder="Например, ежедневно, но не больше 30 постов в месяц"></textarea>
            </div>
            <div class="field field-wide">
              <button class="btn-primary" type="submit">Сохранить график</button>
            </div>
          </form>
        </section>

        <section class="panel section">
          <div class="section-head">
            <div>
              <h2 class="section-title">Площадки</h2>
              <p class="section-subtitle">Список каналов и групп.</p>
            </div>
          </div>
          <div id="outletsTable"></div>
        </section>
      </div>
    </section>
  </div>

  <script>
    const state = { year: String(new Date().getFullYear()) };
    const flash = document.getElementById("flash");

    function todayIso() {
      return new Date().toISOString().slice(0, 10);
    }

    function formatDate(value) {
      if (!value) return "—";
      const [year, month, day] = String(value).split("-");
      if (!year || !month || !day) return value;
      return `${day}.${month}.${year}`;
    }

    function escapeHtml(value) {
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function showFlash(kind, message) {
      flash.className = `flash show ${kind}`;
      flash.textContent = message;
      window.clearTimeout(showFlash.timer);
      showFlash.timer = window.setTimeout(() => {
        flash.className = "flash";
        flash.textContent = "";
      }, 3200);
    }

    async function api(url, options = {}) {
      const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Не удалось выполнить запрос");
      }
      return data;
    }

    function renderStats(summary) {
      const stats = [
        ["Активных графиков", summary.total_campaigns, "На выбранный год"],
        ["Запланировано постов", summary.planned_posts, "По правилам кампаний"],
        ["Уже размещено", summary.done_posts, "По полю «размещено до»"],
        ["Осталось", summary.remaining_posts, "Еще нужно разместить"],
        ["Нужно оплатить", summary.need_payment_campaigns, "До конца оплаты или периода 3 дня и меньше"],
        ["Закрепы к обновлению", summary.pin_due_count, "Обновить сегодня или в ближайшие 3 дня"],
        ["Просроченных графиков", summary.overdue_campaigns, "Есть отставание по выкладке"],
      ];
      document.getElementById("stats").innerHTML = stats.map(([label, value, note]) => `
        <article class="panel stat-card">
          <span class="stat-label">${label}</span>
          <div class="stat-value">${value}</div>
          <div class="stat-note">${note}</div>
        </article>
      `).join("");
    }

    function renderYears(years) {
      const currentYear = String(new Date().getFullYear());
      const allYears = Array.from(new Set([currentYear, ...years])).sort();
      if (!allYears.includes(state.year)) state.year = currentYear;
      document.getElementById("yearSelect").innerHTML = allYears.map((year) => `
        <option value="${year}" ${year === state.year ? "selected" : ""}>${year}</option>
      `).join("");
    }

    function toneByUrgency(urgency) {
      if (urgency === "Просрочено" || urgency === "НУЖНО ОПЛАТИТЬ" || urgency === "Обновить закреп") return "danger";
      if (urgency === "Нужно выложить сегодня" || urgency === "Скоро обновить закреп") return "warn";
      return "ok";
    }

    function postingModeLabel(mode, postsPerMonth) {
      if (mode === "daily_full") return "Ежедневно без пропусков";
      return `Ежедневно, до ${postsPerMonth} постов в месяц`;
    }

    function updateBlock(campaign) {
      return `
        <div class="actions">
          <input class="inline-date" type="date" id="placed-until-${campaign.id}" value="${campaign.placed_until || ""}">
          <button class="btn-secondary" onclick="savePlacedUntil(${campaign.id})">Сохранить размещение</button>
          <button class="btn-ghost" onclick="markPlacedToday(${campaign.id})">До сегодня</button>
        </div>
        <div class="actions">
          <input class="inline-date" type="date" id="paid-until-${campaign.id}" value="${campaign.paid_until || ""}">
          <button class="btn-secondary" onclick="savePaidUntil(${campaign.id})">Сохранить оплату</button>
        </div>
      `;
    }

    function pinUpdateBlock(item) {
      return `
        <div class="actions">
          <input class="inline-date" type="date" id="pin-last-updated-${item.id}" value="${item.last_updated || ""}">
          <button class="btn-secondary" onclick="savePinUpdated(${item.id})">Сохранить дату</button>
          <button class="btn-ghost" onclick="markPinUpdatedToday(${item.id})">Обновила сегодня</button>
        </div>
      `;
    }

    function renderAgenda(items) {
      const root = document.getElementById("agenda");
      if (!items.length) {
        root.innerHTML = `<div class="empty">На сегодня срочных выкладок нет.</div>`;
        return;
      }

      root.innerHTML = items.map((item) => `
        <article class="agenda-card" data-tone="${toneByUrgency(item.urgency)}">
          <div class="agenda-top">
            <div>
              <p class="agenda-title">${escapeHtml(item.name)}</p>
              <div class="meta">
                <span>${escapeHtml(item.platform)}</span>
                <span>${escapeHtml(item.ad_format || "Посты")}</span>
                ${item.kind === "pin_post"
                  ? `<span>${escapeHtml(item.title)}</span><span>${item.remind_every_days} дней</span>`
                  : `<span>${escapeHtml(item.paid_status)}</span><span>${escapeHtml(postingModeLabel(item.posting_mode, item.posts_per_month))}</span>`}
              </div>
            </div>
            <span class="pill tone-${toneByUrgency(item.urgency)}">${escapeHtml(item.urgency)}</span>
          </div>
          ${item.kind === "pin_post"
            ? `<div class="meta">
                <span>Последнее обновление: <strong>${formatDate(item.last_updated)}</strong></span>
                <span>Следующее напоминание: <strong>${formatDate(item.next_due_date)}</strong></span>
                <span>Статус: <strong>${escapeHtml(item.status_label)}</strong></span>
              </div>`
            : `<div class="meta">
                <span>Период: <strong>${formatDate(item.start_date)} - ${formatDate(item.end_date)}</strong></span>
                <span>Оплачено до: <strong>${formatDate(item.paid_until)}</strong></span>
                <span>Размещено до: <strong>${formatDate(item.placed_until)}</strong></span>
                <span>Следующий пост: <strong>${formatDate(item.next_due_date)}</strong></span>
                <span>Прогресс: <strong>${item.done_posts} / ${item.planned_posts}</strong></span>
              </div>`}
          ${item.link ? `<div><a class="inline-link" href="${escapeHtml(item.link)}" target="_blank" rel="noreferrer">Открыть канал</a></div>` : ""}
          ${(item.manager_name || item.manager_link) ? `<div class="muted">Администратор: ${item.manager_link ? `<a class="inline-link" href="${escapeHtml(item.manager_link)}" target="_blank" rel="noreferrer">${escapeHtml(item.manager_name || item.manager_link)}</a>` : escapeHtml(item.manager_name)}</div>` : ""}
          ${(item.comment || item.note) ? `<div class="muted">${escapeHtml(item.comment || item.note)}</div>` : ""}
          ${item.kind === "pin_post" ? pinUpdateBlock(item) : updateBlock(item)}
        </article>
      `).join("");
    }

    function renderCampaigns(items) {
      const root = document.getElementById("campaignsTable");
      if (!items.length) {
        root.innerHTML = `<div class="empty">На выбранный год графиков пока нет.</div>`;
        return;
      }

      root.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Где</th>
              <th>Период</th>
              <th>Правило</th>
              <th>Размещено до</th>
              <th>Следующий пост</th>
              <th>Статус</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            ${items.map((item) => `
              <tr>
                <td>
                  <strong>${escapeHtml(item.name)}</strong><br>
                  <span class="muted">${escapeHtml(item.platform)} · ${escapeHtml(item.ad_format || "Посты")}</span>
                  ${(item.manager_name || item.manager_link) ? `<br><span class="muted">Администратор: ${item.manager_link ? `<a class="inline-link" href="${escapeHtml(item.manager_link)}" target="_blank" rel="noreferrer">${escapeHtml(item.manager_name || item.manager_link)}</a>` : escapeHtml(item.manager_name)}</span>` : ""}
                </td>
                <td>${formatDate(item.start_date)}<br><span class="muted">${formatDate(item.end_date)}</span></td>
                <td>${escapeHtml(postingModeLabel(item.posting_mode, item.posts_per_month))}</td>
                <td>Оплачено до: ${formatDate(item.paid_until)}<br><span class="muted">Размещено до: ${formatDate(item.placed_until)}</span><br><span class="muted">${item.done_posts} из ${item.planned_posts}</span></td>
                <td>${formatDate(item.next_due_date)}</td>
                <td>${escapeHtml(item.status_label)}</td>
                <td>${updateBlock(item)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderOutlets(items) {
      const select = document.getElementById("outletId");
      if (!items.length) {
        select.innerHTML = `<option value="">Сначала добавь площадку</option>`;
      } else {
        select.innerHTML = items.map((item) => `
          <option value="${item.id}">${escapeHtml(item.platform)} · ${escapeHtml(item.name)}</option>
        `).join("");
      }

      const root = document.getElementById("outletsTable");
      if (!items.length) {
        root.innerHTML = `<div class="empty">Площадок пока нет.</div>`;
        return;
      }

      root.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Площадка</th>
              <th>Название</th>
              <th>Формат</th>
              <th>Контакт</th>
              <th>Ссылка</th>
            </tr>
          </thead>
          <tbody>
            ${items.map((item) => `
              <tr>
                <td>${escapeHtml(item.platform)}</td>
                <td><strong>${escapeHtml(item.name)}</strong></td>
                <td>${escapeHtml(item.ad_format || "—")}</td>
                <td>${item.manager_link ? `<a class="inline-link" href="${escapeHtml(item.manager_link)}" target="_blank" rel="noreferrer">${escapeHtml(item.manager_name || item.manager_link)}</a>` : escapeHtml(item.manager_name || "—")}</td>
                <td>${item.link ? `<a class="inline-link" href="${escapeHtml(item.link)}" target="_blank" rel="noreferrer">${escapeHtml(item.link)}</a>` : `<span class="muted">Без ссылки</span>`}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    async function loadOutlets() {
      const data = await api("/api/outlets");
      renderOutlets(data.outlets);
    }

    async function loadDashboard() {
      const data = await api(`/api/dashboard?year=${encodeURIComponent(state.year)}`);
      document.getElementById("todayLabel").textContent = `${data.today_label} · ${state.year}`;
      renderYears(data.years);
      renderStats(data.summary);
      renderAgenda(data.agenda);
      renderCampaigns(data.campaigns);
    }

    async function refreshAll() {
      await loadOutlets();
      await loadDashboard();
    }

    async function savePlacedUntil(id) {
      const value = document.getElementById(`placed-until-${id}`).value;
      await api(`/api/campaigns/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ placed_until: value || null }),
      });
      showFlash("ok", "Дата обновлена.");
      await loadDashboard();
    }

    async function markPlacedToday(id) {
      await api(`/api/campaigns/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ placed_until: todayIso() }),
      });
      showFlash("ok", "Отметила размещение до сегодняшней даты.");
      await loadDashboard();
    }

    async function savePaidUntil(id) {
      const value = document.getElementById(`paid-until-${id}`).value;
      await api(`/api/campaigns/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ paid_until: value || null }),
      });
      showFlash("ok", "Дата оплаты обновлена.");
      await loadDashboard();
    }

    async function savePinUpdated(id) {
      const value = document.getElementById(`pin-last-updated-${id}`).value;
      await api(`/api/pin-posts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ last_updated: value || null }),
      });
      showFlash("ok", "Дата обновления закрепа сохранена.");
      await loadDashboard();
    }

    async function markPinUpdatedToday(id) {
      await api(`/api/pin-posts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ last_updated: todayIso() }),
      });
      showFlash("ok", "Закреп отмечен как обновленный сегодня.");
      await loadDashboard();
    }

    document.getElementById("yearSelect").addEventListener("change", async (event) => {
      state.year = event.target.value;
      await loadDashboard();
    });

    document.getElementById("outletForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      await api("/api/outlets", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      event.currentTarget.reset();
      showFlash("ok", "Площадка сохранена.");
      await refreshAll();
    });

    document.getElementById("campaignForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      await api("/api/campaigns", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      event.currentTarget.reset();
      document.getElementById("campaignYear").value = state.year;
      showFlash("ok", "График сохранен.");
      await loadDashboard();
    });

    document.getElementById("campaignYear").value = String(new Date().getFullYear());

    refreshAll().catch((error) => {
      showFlash("error", error.message);
    });

    window.savePlacedUntil = savePlacedUntil;
    window.markPlacedToday = markPlacedToday;
    window.savePaidUntil = savePaidUntil;
    window.savePinUpdated = savePinUpdated;
    window.markPinUpdatedToday = markPinUpdatedToday;
  </script>
</body>
</html>
"""


@dataclass
class CampaignProgress:
    planned_posts: int
    done_posts: int
    remaining_posts: int
    next_due_date: Optional[str]


@dataclass
class PinReminder:
    next_due_date: str
    days_overdue: int


def ensure_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outlets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                name TEXT NOT NULL,
                link TEXT,
                ad_format TEXT,
                manager_name TEXT,
                manager_link TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(outlets)").fetchall()
        }
        if "manager_name" not in columns:
            conn.execute("ALTER TABLE outlets ADD COLUMN manager_name TEXT")
        if "manager_link" not in columns:
            conn.execute("ALTER TABLE outlets ADD COLUMN manager_link TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outlet_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                posting_mode TEXT NOT NULL DEFAULT 'daily_month_cap',
                posts_per_month INTEGER NOT NULL DEFAULT 30,
                paid_status TEXT NOT NULL DEFAULT 'не оплачено',
                paid_until TEXT,
                placed_until TEXT,
                comment TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(outlet_id) REFERENCES outlets(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pin_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outlet_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'Закреп',
                paid_status TEXT NOT NULL DEFAULT 'оплачено',
                last_updated TEXT NOT NULL,
                remind_every_days INTEGER NOT NULL DEFAULT 14,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(outlet_id) REFERENCES outlets(id) ON DELETE CASCADE
            )
            """
        )
        campaign_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()
        }
        if "posting_mode" not in campaign_columns:
            conn.execute("ALTER TABLE campaigns ADD COLUMN posting_mode TEXT NOT NULL DEFAULT 'daily_month_cap'")
        if "paid_until" not in campaign_columns:
            conn.execute("ALTER TABLE campaigns ADD COLUMN paid_until TEXT")
        conn.commit()


def db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def parse_json_payload(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Неверный JSON в запросе.") from exc


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_int(value: Any, *, default: Optional[int] = None) -> Optional[int]:
    text = clean_text(value)
    if text is None:
      return default
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError("Нужно целое число.") from exc


def clean_date(value: Any, *, required: bool = False) -> Optional[str]:
    text = clean_text(value)
    if text is None:
        if required:
            raise ValueError("Нужна дата.")
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД.") from exc


def month_iterator(start: date, end: date) -> List[date]:
    months: List[date] = []
    current = date(start.year, start.month, 1)
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def scheduled_dates(start_iso: str, end_iso: str, posts_per_month: int, posting_mode: str) -> List[date]:
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    result: List[date] = []

    if posting_mode == "daily_full":
        current = start
        while current <= end:
            result.append(current)
            current += timedelta(days=1)
        return result

    for month_start in month_iterator(start, end):
        last_day = monthrange(month_start.year, month_start.month)[1]
        month_end = date(month_start.year, month_start.month, last_day)
        range_start = max(start, month_start)
        range_end = min(end, month_end)
        if range_start > range_end:
            continue

        days = []
        current = range_start
        while current <= range_end:
            days.append(current)
            current += timedelta(days=1)

        limit = min(posts_per_month, len(days))
        result.extend(days[:limit])

    return result


def campaign_progress(
    start_iso: str,
    end_iso: str,
    posts_per_month: int,
    posting_mode: str,
    placed_until_iso: Optional[str],
) -> CampaignProgress:
    plan = scheduled_dates(start_iso, end_iso, posts_per_month, posting_mode)
    if placed_until_iso:
        placed_until = date.fromisoformat(placed_until_iso)
        done_posts = len([day for day in plan if day <= placed_until])
    else:
        done_posts = 0

    remaining_posts = max(len(plan) - done_posts, 0)
    next_due = plan[done_posts] if done_posts < len(plan) else None
    return CampaignProgress(
        planned_posts=len(plan),
        done_posts=done_posts,
        remaining_posts=remaining_posts,
        next_due_date=next_due.isoformat() if next_due else None,
    )


def pin_progress(last_updated_iso: str, remind_every_days: int, today_iso: str) -> PinReminder:
    last_updated = date.fromisoformat(last_updated_iso)
    next_due = last_updated + timedelta(days=remind_every_days)
    today = date.fromisoformat(today_iso)
    return PinReminder(
        next_due_date=next_due.isoformat(),
        days_overdue=(today - next_due).days,
    )


def serialize_outlet(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "platform": row["platform"],
        "name": row["name"],
        "link": row["link"] or "",
        "ad_format": row["ad_format"] or "",
        "manager_name": row["manager_name"] or "",
        "manager_link": row["manager_link"] or "",
        "notes": row["notes"] or "",
    }


def campaign_status_label(
    progress: CampaignProgress,
    today_iso: str,
    end_date: str,
    paid_until: Optional[str],
) -> str:
    today = date.fromisoformat(today_iso)
    end_dt = date.fromisoformat(end_date)
    days_to_end = (end_dt - today).days
    if paid_until:
        paid_dt = date.fromisoformat(paid_until)
        days_to_paid = (paid_dt - today).days
    else:
        days_to_paid = None

    if (days_to_paid is not None and days_to_paid <= 3) or days_to_end <= 3:
        return "НУЖНО ОПЛАТИТЬ"
    if progress.remaining_posts == 0:
        return "План закрыт"
    if progress.next_due_date and progress.next_due_date < today_iso:
        return "Просрочено"
    if progress.next_due_date == today_iso:
        return "Нужно выложить сегодня"
    if progress.next_due_date and progress.next_due_date <= (date.fromisoformat(today_iso) + timedelta(days=3)).isoformat():
        return "Скоро публикация"
    if end_date < today_iso:
        return "Период завершен"
    return "По графику"


def serialize_campaign(row: sqlite3.Row, *, today_iso: str) -> Dict[str, Any]:
    progress = campaign_progress(
        row["start_date"],
        row["end_date"],
        int(row["posts_per_month"]),
        row["posting_mode"],
        row["placed_until"],
    )
    status = campaign_status_label(progress, today_iso, row["end_date"], row["paid_until"])
    return {
        "id": row["id"],
        "outlet_id": row["outlet_id"],
        "platform": row["platform"],
        "name": row["name"],
        "link": row["link"] or "",
        "ad_format": row["ad_format"] or "",
        "manager_name": row["manager_name"] or "",
        "manager_link": row["manager_link"] or "",
        "year": row["year"],
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "posting_mode": row["posting_mode"],
        "posts_per_month": int(row["posts_per_month"]),
        "paid_status": row["paid_status"],
        "paid_until": row["paid_until"],
        "placed_until": row["placed_until"],
        "comment": row["comment"] or "",
        "planned_posts": progress.planned_posts,
        "done_posts": progress.done_posts,
        "remaining_posts": progress.remaining_posts,
        "next_due_date": progress.next_due_date,
        "status_label": status,
    }


def serialize_pin_post(row: sqlite3.Row, *, today_iso: str) -> Dict[str, Any]:
    progress = pin_progress(row["last_updated"], int(row["remind_every_days"]), today_iso)
    status = "Обновить закреп"
    if progress.days_overdue > 0:
        urgency = "Просрочено"
    elif progress.days_overdue == 0:
        urgency = "Обновить закреп"
    elif progress.days_overdue >= -3:
        urgency = "Скоро обновить закреп"
    else:
        urgency = "По графику"
    return {
        "id": row["id"],
        "kind": "pin_post",
        "outlet_id": row["outlet_id"],
        "platform": row["platform"],
        "name": row["name"],
        "link": row["link"] or "",
        "ad_format": row["ad_format"] or "",
        "manager_name": row["manager_name"] or "",
        "manager_link": row["manager_link"] or "",
        "title": row["title"],
        "paid_status": row["paid_status"],
        "last_updated": row["last_updated"],
        "remind_every_days": int(row["remind_every_days"]),
        "next_due_date": progress.next_due_date,
        "days_overdue": progress.days_overdue,
        "note": row["note"] or "",
        "status_label": status,
        "urgency": urgency,
    }


def list_outlets() -> List[Dict[str, Any]]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, platform, name, link, ad_format, manager_name, manager_link, notes
            FROM outlets
            ORDER BY platform, name
            """
        ).fetchall()
    return [serialize_outlet(row) for row in rows]


def list_campaigns(year: Optional[str] = None) -> List[Dict[str, Any]]:
    query = """
        SELECT
            campaigns.id,
            campaigns.outlet_id,
            campaigns.year,
            campaigns.start_date,
            campaigns.end_date,
            campaigns.posting_mode,
            campaigns.posts_per_month,
            campaigns.paid_status,
            campaigns.paid_until,
            campaigns.placed_until,
            campaigns.comment,
            outlets.platform,
            outlets.name,
            outlets.link,
            outlets.ad_format,
            outlets.manager_name,
            outlets.manager_link
        FROM campaigns
        JOIN outlets ON outlets.id = campaigns.outlet_id
    """
    params: List[Any] = []
    if year:
        query += " WHERE campaigns.year = ? "
        params.append(int(year))
    query += " ORDER BY campaigns.start_date, outlets.platform, outlets.name "

    with db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    today_iso = date.today().isoformat()
    return [serialize_campaign(row, today_iso=today_iso) for row in rows]


def list_pin_posts(year: Optional[str] = None) -> List[Dict[str, Any]]:
    query = """
        SELECT
            pin_posts.id,
            pin_posts.outlet_id,
            pin_posts.title,
            pin_posts.paid_status,
            pin_posts.last_updated,
            pin_posts.remind_every_days,
            pin_posts.note,
            outlets.platform,
            outlets.name,
            outlets.link,
            outlets.ad_format,
            outlets.manager_name,
            outlets.manager_link
        FROM pin_posts
        JOIN outlets ON outlets.id = pin_posts.outlet_id
    """
    params: List[Any] = []
    if year:
        query += " WHERE substr(pin_posts.last_updated, 1, 4) = ? "
        params.append(year)
    query += " ORDER BY pin_posts.last_updated, outlets.platform, outlets.name "

    with db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    today_iso = date.today().isoformat()
    return [serialize_pin_post(row, today_iso=today_iso) for row in rows]


def distinct_years() -> List[str]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT year
            FROM campaigns
            ORDER BY year
            """
        ).fetchall()
    return [str(row["year"]) for row in rows]


def build_dashboard(year: str) -> Dict[str, Any]:
    campaigns = list_campaigns(year)
    pin_posts = list_pin_posts(year)
    today = date.today()
    today_iso = today.isoformat()
    soon_iso = (today + timedelta(days=3)).isoformat()

    agenda: List[Dict[str, Any]] = []
    overdue = 0
    need_payment = 0
    for item in campaigns:
        urgency = None
        next_due = item["next_due_date"]
        paid_until = item["paid_until"]
        end_date = item["end_date"]
        days_to_end = (date.fromisoformat(end_date) - today).days
        days_to_paid = None
        if paid_until:
            days_to_paid = (date.fromisoformat(paid_until) - today).days

        if (days_to_paid is not None and days_to_paid <= 3) or days_to_end <= 3:
            urgency = "НУЖНО ОПЛАТИТЬ"
            need_payment += 1
        elif item["remaining_posts"] == 0:
            continue
        elif next_due and next_due < today_iso:
            urgency = "Просрочено"
            overdue += 1
        elif next_due == today_iso:
            urgency = "Нужно выложить сегодня"
        elif next_due and next_due <= soon_iso:
            urgency = "Скоро публикация"

        if urgency:
            item_copy = dict(item)
            item_copy["kind"] = "campaign"
            item_copy["urgency"] = urgency
            agenda.append(item_copy)

    pin_due_count = 0
    for item in pin_posts:
        if item["urgency"] == "По графику":
            continue
        if item["urgency"] in {"Просрочено", "Обновить закреп"}:
            pin_due_count += 1
        agenda.append(item)

    def agenda_sort_key(item: Dict[str, Any]) -> Any:
        priority = {
            "НУЖНО ОПЛАТИТЬ": 0,
            "Просрочено": 1,
            "Обновить закреп": 2,
            "Нужно выложить сегодня": 3,
            "Скоро обновить закреп": 4,
            "Скоро публикация": 5,
        }
        return (priority.get(item["urgency"], 9), item.get("next_due_date") or "", item["name"])

    agenda.sort(key=agenda_sort_key)

    planned_posts = sum(item["planned_posts"] for item in campaigns)
    done_posts = sum(item["done_posts"] for item in campaigns)

    return {
        "today_label": today.strftime("%d.%m.%Y"),
        "years": distinct_years(),
        "summary": {
            "total_campaigns": len(campaigns),
            "planned_posts": planned_posts,
            "done_posts": done_posts,
            "remaining_posts": max(planned_posts - done_posts, 0),
            "overdue_campaigns": overdue,
            "need_payment_campaigns": need_payment,
            "pin_due_count": pin_due_count,
        },
        "agenda": agenda,
        "campaigns": campaigns,
        "pin_posts": pin_posts,
    }


def insert_outlet(payload: Dict[str, Any]) -> Dict[str, Any]:
    platform = clean_text(payload.get("platform"))
    name = clean_text(payload.get("name"))
    if not platform or not name:
        raise ValueError("Нужно указать площадку и название.")

    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO outlets(platform, name, link, ad_format, manager_name, manager_link, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                platform,
                name,
                clean_text(payload.get("link")),
                clean_text(payload.get("ad_format")),
                clean_text(payload.get("manager_name")),
                clean_text(payload.get("manager_link")),
                clean_text(payload.get("notes")),
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id, platform, name, link, ad_format, manager_name, manager_link, notes
            FROM outlets
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return serialize_outlet(row)


def insert_campaign(payload: Dict[str, Any]) -> Dict[str, Any]:
    outlet_id = clean_int(payload.get("outlet_id"))
    if outlet_id is None:
        raise ValueError("Нужно выбрать площадку.")

    year = clean_int(payload.get("year"))
    posts_per_month = clean_int(payload.get("posts_per_month"), default=30)
    posting_mode = clean_text(payload.get("posting_mode")) or "daily_month_cap"
    if year is None or posts_per_month is None:
        raise ValueError("Нужно указать год и число постов в месяц.")

    start_date = clean_date(payload.get("start_date"), required=True)
    end_date = clean_date(payload.get("end_date"), required=True)
    if start_date > end_date:
        raise ValueError("Дата начала не может быть позже даты конца.")

    with db_connection() as conn:
        outlet_exists = conn.execute("SELECT id FROM outlets WHERE id = ?", (outlet_id,)).fetchone()
        if not outlet_exists:
            raise ValueError("Выбранная площадка не найдена.")

        cursor = conn.execute(
            """
            INSERT INTO campaigns(outlet_id, year, start_date, end_date, posting_mode, posts_per_month, paid_status, paid_until, placed_until, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outlet_id,
                year,
                start_date,
                end_date,
                posting_mode,
                posts_per_month,
                clean_text(payload.get("paid_status")) or "не оплачено",
                clean_date(payload.get("paid_until")),
                clean_date(payload.get("placed_until")),
                clean_text(payload.get("comment")),
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT
                campaigns.id,
                campaigns.outlet_id,
            campaigns.year,
            campaigns.start_date,
            campaigns.end_date,
            campaigns.posting_mode,
            campaigns.posts_per_month,
            campaigns.paid_status,
            campaigns.paid_until,
            campaigns.placed_until,
            campaigns.comment,
                outlets.platform,
                outlets.name,
                outlets.link,
                outlets.ad_format,
                outlets.manager_name,
                outlets.manager_link
            FROM campaigns
            JOIN outlets ON outlets.id = campaigns.outlet_id
            WHERE campaigns.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return serialize_campaign(row, today_iso=date.today().isoformat())


def update_pin_post(pin_post_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    if "last_updated" in payload:
        fields["last_updated"] = clean_date(payload.get("last_updated"), required=True)
    if "note" in payload:
        fields["note"] = clean_text(payload.get("note"))
    if "paid_status" in payload:
        fields["paid_status"] = clean_text(payload.get("paid_status")) or "оплачено"

    if not fields:
        raise ValueError("Нет данных для обновления.")

    assignments = ", ".join(f"{column} = ?" for column in fields)
    values = list(fields.values()) + [pin_post_id]

    with db_connection() as conn:
        existing = conn.execute("SELECT id FROM pin_posts WHERE id = ?", (pin_post_id,)).fetchone()
        if not existing:
            raise ValueError("Закреп не найден.")
        conn.execute(f"UPDATE pin_posts SET {assignments} WHERE id = ?", values)
        conn.commit()
        row = conn.execute(
            """
            SELECT
                pin_posts.id,
                pin_posts.outlet_id,
                pin_posts.title,
                pin_posts.paid_status,
                pin_posts.last_updated,
                pin_posts.remind_every_days,
                pin_posts.note,
                outlets.platform,
                outlets.name,
                outlets.link,
                outlets.ad_format,
                outlets.manager_name,
                outlets.manager_link
            FROM pin_posts
            JOIN outlets ON outlets.id = pin_posts.outlet_id
            WHERE pin_posts.id = ?
            """,
            (pin_post_id,),
        ).fetchone()
    return serialize_pin_post(row, today_iso=date.today().isoformat())


def update_campaign(campaign_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    if "placed_until" in payload:
        fields["placed_until"] = clean_date(payload.get("placed_until"))
    if "paid_status" in payload:
        fields["paid_status"] = clean_text(payload.get("paid_status")) or "не оплачено"
    if "paid_until" in payload:
        fields["paid_until"] = clean_date(payload.get("paid_until"))
    if "comment" in payload:
        fields["comment"] = clean_text(payload.get("comment"))

    if not fields:
        raise ValueError("Нет данных для обновления.")

    assignments = ", ".join(f"{column} = ?" for column in fields)
    values = list(fields.values()) + [campaign_id]

    with db_connection() as conn:
        existing = conn.execute("SELECT id FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if not existing:
            raise ValueError("График не найден.")
        conn.execute(f"UPDATE campaigns SET {assignments} WHERE id = ?", values)
        conn.commit()
        row = conn.execute(
            """
            SELECT
                campaigns.id,
                campaigns.outlet_id,
            campaigns.year,
            campaigns.start_date,
            campaigns.end_date,
            campaigns.posting_mode,
            campaigns.posts_per_month,
            campaigns.paid_status,
            campaigns.paid_until,
            campaigns.placed_until,
            campaigns.comment,
                outlets.platform,
                outlets.name,
                outlets.link,
                outlets.ad_format,
                outlets.manager_name,
                outlets.manager_link
            FROM campaigns
            JOIN outlets ON outlets.id = campaigns.outlet_id
            WHERE campaigns.id = ?
            """,
            (campaign_id,),
        ).fetchone()
    return serialize_campaign(row, today_iso=date.today().isoformat())


class AdsTrackerHandler(BaseHTTPRequestHandler):
    server_version = "AdsTracker/2.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.respond_html(HTML_PAGE)
            return
        if parsed.path == "/healthz":
            self.respond_json({"ok": True})
            return
        if parsed.path == "/api/outlets":
            self.respond_json({"outlets": list_outlets()})
            return
        if parsed.path == "/api/dashboard":
            qs = parse_qs(parsed.query)
            year = qs.get("year", [str(date.today().year)])[0]
            self.respond_json(build_dashboard(year))
            return
        self.respond_json({"error": "Маршрут не найден."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            payload = parse_json_payload(self)
            if self.path == "/api/outlets":
                self.respond_json({"outlet": insert_outlet(payload)}, status=HTTPStatus.CREATED)
                return
            if self.path == "/api/campaigns":
                self.respond_json({"campaign": insert_campaign(payload)}, status=HTTPStatus.CREATED)
                return
            self.respond_json({"error": "Маршрут не найден."}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.respond_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            self.respond_json({"error": f"Внутренняя ошибка: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        try:
            if len(parts) == 3 and parts[:2] == ["api", "campaigns"]:
                payload = parse_json_payload(self)
                campaign_id = int(parts[2])
                self.respond_json({"campaign": update_campaign(campaign_id, payload)})
                return
            if len(parts) == 3 and parts[:2] == ["api", "pin-posts"]:
                payload = parse_json_payload(self)
                pin_post_id = int(parts[2])
                self.respond_json({"pin_post": update_pin_post(pin_post_id, payload)})
                return
            self.respond_json({"error": "Маршрут не найден."}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.respond_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            self.respond_json({"error": f"Внутренняя ошибка: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, fmt: str, *args: Any) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} - {fmt % args}")

    def respond_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def respond_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Локальный планировщик регулярных рекламных размещений.")
    parser.add_argument("--host", default=HOST, help="Адрес запуска сервера.")
    parser.add_argument("--port", type=int, default=PORT, help="Порт запуска сервера.")
    return parser.parse_args()


def main() -> None:
    ensure_db()
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AdsTrackerHandler)
    print(f"Открой в браузере: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
