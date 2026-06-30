/** @odoo-module **/

import { Component, onMounted, onPatched, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class VlfDashboardClientAction extends Component {
    static template = "vlf_dashboard_pro_ferre.DashboardClientAction";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.timer = null;
        const params = (this.props.action && this.props.action.params) || {};
        this.state = useState({
            catalog: [],
            dashboard: {},
            items: [],
            filters: {
                date_from: "",
                date_to: "",
                company_id: "",
                custom: {},
            },
            selectedDashboardId: params.dashboard_id || false,
            loading: false,
            builderOpen: false,
            helpOpen: false,
            filterSuggestionsOpen: true,
            builder: { chart_types: [], presets: [] },
            draggingCardId: false,
        });
        onWillStart(async () => {
            await this.loadBuilderCatalog();
            await this.loadDashboard(this.state.selectedDashboardId);
        });
        onMounted(() => {
            this.renderAll();
            this.resetTimer();
        });
        onPatched(() => {
            this.renderAll();
        });
        onWillUnmount(() => {
            this.clearTimer();
        });
    }

    async loadBuilderCatalog() {
        try {
            const catalog = await this.orm.call("vlf.dashboard", "get_builder_catalog", []);
            this.state.builder = catalog || { chart_types: [], presets: [] };
        } catch (error) {
            this.state.builder = { chart_types: [], presets: [] };
        }
    }

    toggleBuilder() {
        this.state.builderOpen = !this.state.builderOpen;
    }

    toggleHelp() {
        this.state.helpOpen = !this.state.helpOpen;
    }

    toggleFilterSuggestions() {
        this.state.filterSuggestionsOpen = !this.state.filterSuggestionsOpen;
    }

    async addSuggestedFilter(key) {
        if (!this.state.dashboard.id || !key) return;
        this.state.loading = true;
        try {
            const result = await this.orm.call("vlf.dashboard", "add_filter_from_suggestion", [this.state.dashboard.id, key]);
            this.notification.add(result.already_exists ? `El filtro ya existía: ${result.name}` : `Filtro agregado: ${result.name}`, { type: "success" });
            await this.loadDashboard(this.state.dashboard.id);
        } catch (error) {
            this.notification.add(error.message || "No se pudo agregar el filtro", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async openDashboardConfig() {
        if (!this.state.dashboard.id) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Configurar dashboard",
            res_model: "vlf.dashboard",
            res_id: this.state.dashboard.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onBuilderDragStart(ev, kind, key) {
        const payload = { kind, key };
        ev.dataTransfer.setData("application/vnd.vlf-dashboard-builder", JSON.stringify(payload));
        ev.dataTransfer.effectAllowed = "copy";
    }

    onGridDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
    }

    async onGridDrop(ev) {
        ev.preventDefault();
        const payload = this._readDragPayload(ev);
        if (!payload || payload.kind === "reorder") return;
        await this.createBuilderItem(payload.kind, payload.key);
    }

    onCardDragStart(ev, itemId) {
        if (!this.state.dashboard.allow_instant_edit) return;
        const button = ev.target.closest && ev.target.closest("button");
        if (button) {
            ev.preventDefault();
            return;
        }
        this.state.draggingCardId = itemId;
        ev.dataTransfer.setData("application/vnd.vlf-dashboard-builder", JSON.stringify({ kind: "reorder", item_id: itemId }));
        ev.dataTransfer.effectAllowed = "move";
    }

    onCardDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
    }

    async onCardDrop(ev, targetItemId) {
        ev.preventDefault();
        ev.stopPropagation();
        const payload = this._readDragPayload(ev);
        if (!payload) return;
        if (payload.kind === "reorder") {
            await this.reorderCard(payload.item_id, targetItemId);
        } else {
            await this.createBuilderItem(payload.kind, payload.key);
        }
    }

    _readDragPayload(ev) {
        try {
            const raw = ev.dataTransfer.getData("application/vnd.vlf-dashboard-builder");
            return raw ? JSON.parse(raw) : false;
        } catch (error) {
            return false;
        }
    }

    async createBuilderItem(kind, key) {
        if (!this.state.dashboard.id) return;
        this.state.loading = true;
        try {
            const result = await this.orm.call("vlf.dashboard", "create_item_from_builder", [this.state.dashboard.id, { kind, key }]);
            this.notification.add(`Elemento agregado: ${result.name}`, { type: "success" });
            await this.loadDashboard(this.state.dashboard.id);
        } catch (error) {
            this.notification.add(error.message || "No se pudo agregar el elemento", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async reorderCard(sourceItemId, targetItemId) {
        sourceItemId = parseInt(sourceItemId);
        targetItemId = parseInt(targetItemId);
        if (!sourceItemId || !targetItemId || sourceItemId === targetItemId) return;
        const ordered = this.state.items.map((item) => item.id).filter((id) => id !== sourceItemId);
        const index = ordered.indexOf(targetItemId);
        if (index >= 0) {
            ordered.splice(index, 0, sourceItemId);
        } else {
            ordered.push(sourceItemId);
        }
        await this.orm.call("vlf.dashboard", "reorder_items", [this.state.dashboard.id, ordered]);
        this.notification.add("Orden del dashboard actualizado", { type: "success" });
        await this.loadDashboard(this.state.dashboard.id);
    }

    async loadDashboard(dashboardId=false) {
        this.state.loading = true;
        const payload = await this.orm.call("vlf.dashboard", "get_dashboard_payload", [dashboardId || false, this.state.filters]);
        this.state.catalog = payload.catalog || [];
        this.state.dashboard = payload.dashboard || {};
        this.state.items = payload.items || [];
        this.state.selectedDashboardId = this.state.dashboard.id || false;
        this.state.loading = false;
        this.resetTimer();
    }

    async reload() {
        await this.loadDashboard(this.state.selectedDashboardId);
        this.notification.add("Dashboard actualizado", { type: "success" });
    }

    clearTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    resetTimer() {
        this.clearTimer();
        if (this.state.dashboard && this.state.dashboard.auto_refresh) {
            const seconds = Math.max(parseInt(this.state.dashboard.auto_refresh_seconds || 60), 10);
            this.timer = setInterval(() => this.loadDashboard(this.state.selectedDashboardId), seconds * 1000);
        }
    }

    async onDashboardChange(ev) {
        await this.loadDashboard(parseInt(ev.target.value));
    }

    onDateFromChange(ev) { this.state.filters.date_from = ev.target.value || ""; }
    onDateToChange(ev) { this.state.filters.date_to = ev.target.value || ""; }
    onCompanyChange(ev) { this.state.filters.company_id = ev.target.value || ""; }
    onCustomFilterChange(ev, key, valueType) {
        if (!this.state.filters.custom) this.state.filters.custom = {};
        if (valueType === "boolean") {
            this.state.filters.custom[key] = ev.target.checked ? "1" : "0";
        } else {
            this.state.filters.custom[key] = ev.target.value || "";
        }
    }

    customFilterValue(key) {
        return (this.state.filters.custom && this.state.filters.custom[key]) || "";
    }

    async applyFilters() {
        await this.loadDashboard(this.state.selectedDashboardId);
    }

    async clearFilters() {
        this.state.filters.date_from = "";
        this.state.filters.date_to = "";
        this.state.filters.company_id = "";
        this.state.filters.custom = {};
        await this.loadDashboard(this.state.selectedDashboardId);
    }

    formatNumber(value, item={}) {
        const prefix = item.unit_prefix || "";
        const suffix = item.unit_suffix || "";
        const digits = Number.isInteger(item.precision_digits) ? item.precision_digits : 2;
        let number = Number(value || 0);
        if (item.number_system === "compact") {
            const abs = Math.abs(number);
            if (abs >= 1000000000) return `${prefix}${(number / 1000000000).toFixed(2)}B${suffix}`;
            if (abs >= 1000000) return `${prefix}${(number / 1000000).toFixed(2)}M${suffix}`;
            if (abs >= 1000) return `${prefix}${(number / 1000).toFixed(2)}K${suffix}`;
        }
        if (item.number_system === "indian") {
            const abs = Math.abs(number);
            if (abs >= 10000000) return `${prefix}${(number / 10000000).toFixed(2)}Cr${suffix}`;
            if (abs >= 100000) return `${prefix}${(number / 100000).toFixed(2)}L${suffix}`;
        }
        return `${prefix}${number.toLocaleString(undefined, { maximumFractionDigits: digits })}${suffix}`;
    }

    getItem(id) {
        return this.state.items.find((item) => item.id === id);
    }

    palette(item) {
        const palettes = {
            classic: ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4", "#64748b"],
            business: ["#475569", "#2563eb", "#0f766e", "#9333ea", "#ea580c", "#334155", "#0891b2"],
            pastel: ["#93c5fd", "#fca5a5", "#86efac", "#fde68a", "#c4b5fd", "#a5f3fc", "#cbd5e1"],
            contrast: ["#111827", "#dc2626", "#16a34a", "#ca8a04", "#7c3aed", "#0284c7", "#db2777"],
            mono: ["#111827", "#374151", "#4b5563", "#6b7280", "#9ca3af", "#d1d5db"],
        };
        if (item.custom_color) return [item.custom_color, "#94a3b8", "#cbd5e1"];
        return palettes[item.color_palette || "business"] || palettes.business;
    }

    esc(value) {
        return String(value == null ? "" : value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;");
    }

    renderAll() {
        this.renderCharts();
        this.renderLists();
        this.renderTodos();
    }

    renderCharts() {
        for (const node of document.querySelectorAll(".vlf-chart[data-chart-id]")) {
            const item = this.getItem(parseInt(node.dataset.chartId));
            if (!item) continue;
            const type = item.type;
            let html = "";
            if (type === "bar") html = this.drawBar(item, false);
            else if (type === "horizontal_bar") html = this.drawBar(item, true);
            else if (type === "line") html = this.drawLine(item, false);
            else if (type === "area") html = this.drawLine(item, true);
            else if (type === "pie") html = this.drawPie(item, false);
            else if (type === "doughnut") html = this.drawPie(item, true);
            else if (type === "polar_area") html = this.drawPolar(item);
            else if (type === "flower") html = this.drawFlower(item);
            else if (type === "funnel") html = this.drawFunnel(item);
            else if (type === "radial") html = this.drawRadial(item);
            else if (type === "bullet") html = this.drawBullet(item);
            else if (type === "scatter") html = this.drawScatter(item);
            else if (type === "radar") html = this.drawRadar(item);
            else if (type === "map") html = this.drawMap(item);
            node.innerHTML = html;
        }
    }

    renderLists() {
        for (const node of document.querySelectorAll(".vlf-list-container[data-list-id]")) {
            const item = this.getItem(parseInt(node.dataset.listId));
            if (!item) continue;
            const rows = item.rows || [];
            if (!rows.length) {
                node.innerHTML = `<div class="vlf-muted">Sin datos</div>`;
                continue;
            }
            const keys = Object.keys(rows[0]).slice(0, 8);
            if (item.list_style === "cards") {
                node.innerHTML = `<div class="vlf-mini-cards">${rows.map((row) => `<div class="vlf-mini-card">${keys.map((k) => `<div><strong>${this.esc(k)}:</strong> ${this.esc(row[k])}</div>`).join("")}</div>`).join("")}</div>`;
            } else {
                node.innerHTML = `<table class="vlf-table"><thead><tr>${keys.map((k) => `<th>${this.esc(k)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${keys.map((k) => `<td>${this.esc(row[k])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
            }
        }
    }

    renderTodos() {
        for (const node of document.querySelectorAll(".vlf-todo-container[data-todo-id]")) {
            const item = this.getItem(parseInt(node.dataset.todoId));
            if (!item) continue;
            const rows = item.rows || [];
            node.innerHTML = rows.length ? rows.map((todo) => `
                <div class="vlf-todo-row vlf-todo-${this.esc(todo.state)}">
                    <span class="vlf-todo-state"></span>
                    <div><strong>${this.esc(todo.name)}</strong><small>${this.esc(todo.user || "")} ${this.esc(todo.deadline || "")}</small></div>
                    <span class="vlf-priority">${this.esc(todo.priority || "0")}</span>
                </div>`).join("") : `<div class="vlf-muted">No hay pendientes.</div>`;
        }
    }

    chartBase(item) {
        const values = (item.values || []).map((v) => Number(v || 0));
        const labels = item.labels || [];
        const max = Math.max(...values, Number(item.target_value || 0), 1);
        const colors = this.palette(item);
        return { values, labels, max, colors };
    }

    legend(item, colors) {
        if (!item.show_legend) return "";
        const labels = item.labels || [];
        return `<div class="vlf-legend">${labels.slice(0, 8).map((label, i) => `<span><i style="background:${colors[i % colors.length]}"></i>${this.esc(label)}</span>`).join("")}</div>`;
    }

    drawBar(item, horizontal=false) {
        const { values, labels, max, colors } = this.chartBase(item);
        if (!values.length) return `<div class="vlf-muted">Sin datos</div>`;
        if (horizontal) {
            return `<div class="vlf-hbar-wrap">${values.map((v, i) => `<div class="vlf-hbar-row"><span>${this.esc(labels[i] || "")}</span><div><b style="width:${Math.max((v / max) * 100, 1)}%;background:${colors[i % colors.length]}"></b></div><em>${item.show_values ? this.formatNumber(v, item) : ""}</em></div>`).join("")}</div>`;
        }
        return `<div class="vlf-bar-wrap">${values.map((v, i) => `<div class="vlf-bar-col"><div class="vlf-bar-value">${item.show_values ? this.formatNumber(v, item) : ""}</div><b style="height:${Math.max((v / max) * 100, 1)}%;background:${colors[i % colors.length]}"></b><span>${this.esc(labels[i] || "")}</span></div>`).join("")}</div>`;
    }

    drawLine(item, area=false) {
        const { values, labels, max, colors } = this.chartBase(item);
        if (!values.length) return `<div class="vlf-muted">Sin datos</div>`;
        const w = 640, h = 240, pad = 28;
        const step = values.length > 1 ? (w - 2 * pad) / (values.length - 1) : 0;
        const pts = values.map((v, i) => [pad + i * step, h - pad - (v / max) * (h - 2 * pad)]);
        const pointText = pts.map((p) => p.join(",")).join(" ");
        const areaPts = `${pad},${h - pad} ${pointText} ${w - pad},${h - pad}`;
        return `<svg class="vlf-svg" viewBox="0 0 ${w} ${h}">
            <line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" class="vlf-axis"/>
            ${area ? `<polygon points="${areaPts}" fill="${colors[0]}" opacity="0.18"/>` : ""}
            <polyline points="${pointText}" fill="none" stroke="${colors[0]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
            ${pts.map((p, i) => `<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${colors[i % colors.length]}"><title>${this.esc(labels[i])}: ${this.formatNumber(values[i], item)}</title></circle>`).join("")}
            ${labels.map((label, i) => `<text x="${pad + i * step}" y="${h-6}" text-anchor="middle" class="vlf-svg-label">${this.esc(String(label).slice(0, 8))}</text>`).join("")}
        </svg>${this.legend(item, colors)}`;
    }

    arcPath(cx, cy, r, startAngle, endAngle) {
        const start = this.polar(cx, cy, r, endAngle);
        const end = this.polar(cx, cy, r, startAngle);
        const large = endAngle - startAngle <= 180 ? "0" : "1";
        return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y} Z`;
    }

    polar(cx, cy, r, angle) {
        const rad = (angle - 90) * Math.PI / 180.0;
        return { x: cx + (r * Math.cos(rad)), y: cy + (r * Math.sin(rad)) };
    }

    drawPie(item, donut=false) {
        const { values, colors } = this.chartBase(item);
        const total = values.reduce((a, b) => a + Math.max(b, 0), 0) || 1;
        let angle = 0;
        const slices = values.map((v, i) => {
            const next = angle + (Math.max(v, 0) / total) * 360;
            const path = this.arcPath(120, 120, 100, angle, next);
            angle = next;
            return `<path d="${path}" fill="${colors[i % colors.length]}"><title>${this.esc(item.labels[i])}: ${this.formatNumber(v, item)}</title></path>`;
        }).join("");
        return `<div class="vlf-pie-box"><svg class="vlf-pie" viewBox="0 0 240 240">${slices}${donut ? '<circle cx="120" cy="120" r="56" fill="var(--vlf-card-bg)"/>' : ''}</svg>${this.legend(item, colors)}</div>`;
    }

    drawPolar(item) {
        const { values, labels, max, colors } = this.chartBase(item);
        const count = values.length || 1;
        const angleStep = 360 / count;
        const parts = values.map((v, i) => {
            const r = 25 + (v / max) * 82;
            return `<path d="${this.arcPath(120, 120, r, i * angleStep, (i + 1) * angleStep)}" fill="${colors[i % colors.length]}" opacity="0.72"><title>${this.esc(labels[i])}: ${this.formatNumber(v, item)}</title></path>`;
        }).join("");
        return `<svg class="vlf-pie" viewBox="0 0 240 240">${parts}</svg>${this.legend(item, colors)}`;
    }

    drawFlower(item) {
        const { values, labels, max, colors } = this.chartBase(item);
        const count = values.length || 1;
        const petals = values.map((v, i) => {
            const a = (i / count) * Math.PI * 2;
            const len = 42 + (v / max) * 55;
            const x = 120 + Math.cos(a) * len;
            const y = 120 + Math.sin(a) * len;
            const rx = 16 + (v / max) * 24;
            return `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="20" transform="rotate(${(a * 180 / Math.PI)} ${x} ${y})" fill="${colors[i % colors.length]}" opacity="0.8"><title>${this.esc(labels[i])}: ${this.formatNumber(v, item)}</title></ellipse>`;
        }).join("");
        return `<svg class="vlf-pie" viewBox="0 0 240 240">${petals}<circle cx="120" cy="120" r="28" fill="${colors[0]}"/></svg>${this.legend(item, colors)}`;
    }

    drawFunnel(item) {
        const { values, labels, max, colors } = this.chartBase(item);
        const w = 520;
        return `<div class="vlf-funnel">${values.map((v, i) => {
            const width = Math.max((v / max) * w, 80);
            return `<div class="vlf-funnel-row" style="width:${width}px;background:${colors[i % colors.length]}"><span>${this.esc(labels[i] || "")}</span><b>${item.show_values ? this.formatNumber(v, item) : ""}</b></div>`;
        }).join("")}</div>`;
    }

    drawRadial(item) {
        const { values, colors } = this.chartBase(item);
        const value = values.length ? values[0] : Number(item.total || 0);
        const target = Number(item.target_value || Math.max(value, 1));
        const pct = Math.max(0, Math.min(value / target, 1));
        const c = 2 * Math.PI * 84;
        return `<div class="vlf-radial-box"><svg viewBox="0 0 220 220" class="vlf-radial"><circle cx="110" cy="110" r="84" class="vlf-radial-bg"/><circle cx="110" cy="110" r="84" class="vlf-radial-fg" stroke="${colors[0]}" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - pct)}"/><text x="110" y="104" text-anchor="middle" class="vlf-radial-text">${Math.round(pct * 100)}%</text><text x="110" y="132" text-anchor="middle" class="vlf-radial-sub">${this.formatNumber(value, item)}</text></svg></div>`;
    }

    drawBullet(item) {
        const { values, max, colors } = this.chartBase(item);
        const value = values.length ? values[0] : Number(item.total || 0);
        const target = Number(item.target_value || max);
        const scale = Math.max(value, target, 1);
        return `<div class="vlf-bullet"><div class="vlf-bullet-track"><b style="width:${(value / scale) * 100}%;background:${colors[0]}"></b><i style="left:${(target / scale) * 100}%"></i></div><div class="vlf-bullet-labels"><span>${this.formatNumber(value, item)}</span><span>${item.target_label}: ${this.formatNumber(target, item)}</span></div></div>`;
    }

    drawScatter(item) {
        const { values, labels, max, colors } = this.chartBase(item);
        const w = 640, h = 240, pad = 28;
        const pts = values.map((v, i) => {
            const x = pad + (i / Math.max(values.length - 1, 1)) * (w - 2 * pad);
            const y = h - pad - (v / max) * (h - 2 * pad);
            const r = 5 + Math.min(12, (v / max) * 12);
            return `<circle cx="${x}" cy="${y}" r="${r}" fill="${colors[i % colors.length]}" opacity="0.82"><title>${this.esc(labels[i])}: ${this.formatNumber(v, item)}</title></circle>`;
        }).join("");
        return `<svg class="vlf-svg" viewBox="0 0 ${w} ${h}"><line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" class="vlf-axis"/><line x1="${pad}" y1="${pad}" x2="${pad}" y2="${h-pad}" class="vlf-axis"/>${pts}</svg>${this.legend(item, colors)}`;
    }

    drawRadar(item) {
        const { values, labels, max, colors } = this.chartBase(item);
        const count = values.length || 1;
        const cx = 130, cy = 120, radius = 90;
        const points = values.map((v, i) => {
            const a = -Math.PI / 2 + (i / count) * Math.PI * 2;
            const r = (v / max) * radius;
            return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
        });
        const axes = values.map((v, i) => {
            const a = -Math.PI / 2 + (i / count) * Math.PI * 2;
            return `<line x1="${cx}" y1="${cy}" x2="${cx + Math.cos(a) * radius}" y2="${cy + Math.sin(a) * radius}" class="vlf-axis"/>`;
        }).join("");
        return `<svg class="vlf-pie" viewBox="0 0 260 240">${axes}<polygon points="${points.map((p) => p.join(',')).join(' ')}" fill="${colors[0]}" opacity="0.24" stroke="${colors[0]}" stroke-width="4"/>${points.map((p, i) => `<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${colors[i % colors.length]}"><title>${this.esc(labels[i])}: ${this.formatNumber(values[i], item)}</title></circle>`).join("")}</svg>${this.legend(item, colors)}`;
    }

    drawMap(item) {
        const rows = item.rows || [];
        if (!rows.length) return `<div class="vlf-muted">Sin coordenadas. Use clientes con latitud/longitud.</div>`;
        return `<div class="vlf-map"><div class="vlf-map-grid">${rows.slice(0, 25).map((p, i) => {
            const x = 5 + ((Math.abs(Number(p.lng || i) * 37) % 90));
            const y = 8 + ((Math.abs(Number(p.lat || i) * 29) % 82));
            return `<span class="vlf-map-pin" style="left:${x}%;top:${y}%" title="${this.esc(p.label)}"></span>`;
        }).join("")}</div><div class="vlf-map-list">${rows.slice(0, 8).map((p) => `<span>${this.esc(p.label)}</span>`).join("")}</div></div>`;
    }

    async openRecords(itemId) {
        const action = await this.orm.call("vlf.dashboard.item", "get_item_action", [itemId, this.state.filters]);
        if (action) {
            await this.action.doAction(action);
        }
    }

    async editItem(itemId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Editar item",
            res_model: "vlf.dashboard.item",
            res_id: itemId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async duplicateDashboard() {
        const result = await this.orm.call("vlf.dashboard", "duplicate_dashboard", [this.state.dashboard.id]);
        this.notification.add(`Dashboard duplicado: ${result.name}`, { type: "success" });
        await this.loadDashboard(result.id);
    }

    downloadText(filename, content, mime="text/plain") {
        const blob = new Blob([content], { type: mime });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    }

    async exportJSON() {
        const content = await this.orm.call("vlf.dashboard", "export_dashboard_json", [this.state.dashboard.id]);
        this.downloadText(`${this.state.dashboard.name || 'dashboard'}.json`, content, "application/json");
    }

    exportCSV() {
        const lines = [["Item", "Tipo", "Etiqueta", "Valor"]];
        for (const item of this.state.items) {
            const labels = item.labels || [];
            const values = item.values || [];
            if (labels.length) {
                labels.forEach((label, i) => lines.push([item.name, item.type, label, values[i] || 0]));
            } else {
                lines.push([item.name, item.type, "Total", item.total || 0]);
            }
        }
        const csv = lines.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
        this.downloadText(`${this.state.dashboard.name || 'dashboard'}.csv`, csv, "text/csv");
    }

    async importJSONPrompt() {
        const content = window.prompt("Pega aquí el JSON exportado de otro dashboard:");
        if (!content) return;
        const result = await this.orm.call("vlf.dashboard", "import_dashboard_json", [content]);
        this.notification.add(`Dashboard importado: ${result.name}`, { type: "success" });
        await this.loadDashboard(result.id);
    }

    printDashboard() {
        window.print();
    }

    exportItemPNG(itemId) {
        const chart = document.querySelector(`.vlf-card[data-item-card='${itemId}'] .vlf-chart svg, .vlf-card[data-item-card='${itemId}'] svg`);
        if (!chart) {
            this.notification.add("Este item no tiene SVG exportable. Usa la impresión/PDF para exportarlo.", { type: "warning" });
            return;
        }
        const serializer = new XMLSerializer();
        const svgText = serializer.serializeToString(chart);
        const img = new Image();
        const svgBlob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
        const url = URL.createObjectURL(svgBlob);
        img.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = 900;
            canvas.height = 500;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            URL.revokeObjectURL(url);
            const png = canvas.toDataURL("image/png");
            const link = document.createElement("a");
            link.href = png;
            link.download = `dashboard_item_${itemId}.png`;
            link.click();
        };
        img.src = url;
    }
}

registry.category("actions").add("vlf_dashboard_pro_ferre.client_action", VlfDashboardClientAction);
