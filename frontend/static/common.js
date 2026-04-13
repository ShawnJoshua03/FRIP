/* ================================================================
   FRIP — common.js
   All client-side logic: routing, API calls, rendering
   ================================================================ */
(function () {
    "use strict";

    /* ── State ──────────────────────────────────────────────────── */
    let currentUser = null;          // { user_id, name } or null
    let portfolioChart = null;       // Chart.js instance

    /* ── Helpers ────────────────────────────────────────────────── */
    function $(sel, root) { return (root || document).querySelector(sel); }
    function $$(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

    function money(n) {
        if (n == null) return "$0";
        return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }
    function moneyDecimal(n) {
        return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function pct(n) { return (n * 100).toFixed(2) + "%"; }
    function shortDate(iso) {
        const d = new Date(iso);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    }

    /* ── Toast Notifications ────────────────────────────────────── */
    function toast(msg, type) {
        type = type || "info";
        const el = document.createElement("div");
        el.className = "toast toast-" + type;
        el.innerHTML = '<span>' + msg + '</span><button class="close-toast">&times;</button>';
        $("#toast-container").appendChild(el);
        el.querySelector(".close-toast").onclick = function () { el.remove(); };
        setTimeout(function () { el.remove(); }, 4500);
    }

    /* ── API Fetch Wrapper ──────────────────────────────────────── */
    async function api(url, options) {
        options = options || {};
        const opts = {
            method: options.method || "GET",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
        };
        if (options.body) opts.body = JSON.stringify(options.body);
        const res = await fetch(url, opts);
        const data = await res.json();
        if (!res.ok) {
            throw { status: res.status, message: data.error || "Unknown error" };
        }
        return data;
    }

    /* ── Placeholder SVG Generator ──────────────────────────────── */
    function houseSvg(variant) {
        const colors = [
            { wall: "#1e3a5f", roof: "#0D7377", win: "#14B8A6" },
            { wall: "#2d1b4e", roof: "#0D7377", win: "#A7F3D0" },
            { wall: "#1a2e1a", roof: "#14B8A6", win: "#0D7377" },
        ];
        const c = colors[(variant || 0) % colors.length];
        return '<svg viewBox="0 0 400 260" xmlns="http://www.w3.org/2000/svg">' +
            '<rect width="400" height="260" fill="' + c.wall + '"/>' +
            '<polygon points="200,30 50,120 350,120" fill="' + c.roof + '"/>' +
            '<rect x="120" y="120" width="160" height="110" fill="' + c.roof + '" opacity=".3"/>' +
            '<rect x="145" y="145" width="40" height="40" rx="3" fill="' + c.win + '" opacity=".6"/>' +
            '<rect x="215" y="145" width="40" height="40" rx="3" fill="' + c.win + '" opacity=".6"/>' +
            '<rect x="180" y="190" width="40" height="40" rx="2" fill="' + c.win + '" opacity=".35"/>' +
            '</svg>';
    }

    /* ── Property Card HTML ─────────────────────────────────────── */
    function propCard(p, idx) {
        var funded = p.total_pooled_capital / p.total_value;
        return '<div class="card prop-card" data-pid="' + p._id + '">' +
            '<div class="prop-card-img">' + houseSvg(idx) + '</div>' +
            '<div class="prop-card-body">' +
            '<div class="prop-card-address">' + esc(p.address) + '</div>' +
            '<div class="prop-card-stats">' +
            '<div><div class="prop-card-stat-label">Total Value</div><div class="prop-card-stat-value">' + money(p.total_value) + '</div></div>' +
            '<div><div class="prop-card-stat-label">Funded</div><div class="prop-card-stat-value text-teal">' + (funded * 100).toFixed(1) + '%</div></div>' +
            '<div><div class="prop-card-stat-label">Annual Return</div><div class="prop-card-stat-value">' + p.expected_annual_return + '%</div></div>' +
            '<div><div class="prop-card-stat-label">Monthly Income</div><div class="prop-card-stat-value">' + money(p.rental_income) + '</div></div>' +
            '</div>' +
            '<div class="progress-track"><div class="progress-fill" style="width:' + (funded * 100) + '%"></div></div>' +
            '</div></div>';
    }

    function esc(s) {
        var d = document.createElement("div");
        d.textContent = s;
        return d.innerHTML;
    }

    /* ══════════════════════════════════════════════════════════════
       ROUTING
       ══════════════════════════════════════════════════════════════ */
    const routes = {
        "/":               "page-home",
        "/login":          "page-login",
        "/register":       "page-register",
        "/properties-page":"page-properties",
        "/dashboard":      "page-dashboard",
        "/admin":          "page-admin",
    };

    function navigate(path, push) {
        // property detail route
        var detailMatch = path.match(/^\/property\/(.+)$/);

        // protected routes
        if ((path === "/dashboard" || path === "/admin") && !currentUser) {
            navigate("/login", true);
            return;
        }

        // hide all pages
        $$(".page").forEach(function (p) { p.classList.remove("active"); });

        if (detailMatch) {
            $("#page-detail").classList.add("active");
            loadPropertyDetail(detailMatch[1]);
        } else {
            var pageId = routes[path] || "page-home";
            var el = document.getElementById(pageId);
            if (el) el.classList.add("active");

            // trigger data loads
            if (path === "/" || path === "") loadHome();
            if (path === "/properties-page") loadAllProperties();
            if (path === "/dashboard") loadDashboard();
            if (path === "/admin") loadAdmin();
        }

        if (push !== false) history.pushState(null, "", path);
        window.scrollTo(0, 0);
        closeMobileMenu();
    }

    function closeMobileMenu() {
        var nl = $("#nav-links");
        if (nl) nl.classList.remove("open");
    }

    /* listen to link clicks with data-link */
    document.addEventListener("click", function (e) {
        var a = e.target.closest("[data-link]");
        if (a && a.getAttribute("href")) {
            e.preventDefault();
            navigate(a.getAttribute("href"));
        }
        /* property card click */
        var card = e.target.closest(".prop-card[data-pid]");
        if (card) {
            navigate("/property/" + card.dataset.pid);
        }
    });

    window.addEventListener("popstate", function () {
        navigate(location.pathname, false);
    });

    /* ══════════════════════════════════════════════════════════════
       AUTH
       ══════════════════════════════════════════════════════════════ */
    function updateNav() {
        if (currentUser) {
            $("#nav-guest").classList.add("hidden");
            $("#nav-user").classList.remove("hidden");
        } else {
            $("#nav-guest").classList.remove("hidden");
            $("#nav-user").classList.add("hidden");
        }
    }

    async function checkAuth() {
        try {
            var data = await api("/auth/me");
            if (data.authenticated) {
                currentUser = { user_id: data.user_id, name: data.name };
            } else {
                currentUser = null;
            }
        } catch (e) {
            currentUser = null;
        }
        updateNav();
    }

    /* Register */
    $("#form-register").addEventListener("submit", async function (e) {
        e.preventDefault();
        var errEl = $("#register-error");
        errEl.textContent = "";
        try {
            var data = await api("/auth/register", {
                method: "POST",
                body: {
                    name: $("#reg-name").value.trim(),
                    email: $("#reg-email").value.trim(),
                    password: $("#reg-password").value,
                },
            });
            currentUser = { user_id: data.user_id, name: data.name };
            updateNav();
            toast("Account created! Welcome, " + data.name + ".", "success");
            navigate("/dashboard");
        } catch (err) {
            errEl.textContent = err.message || "Registration failed.";
        }
    });

    /* Login */
    $("#form-login").addEventListener("submit", async function (e) {
        e.preventDefault();
        var errEl = $("#login-error");
        errEl.textContent = "";
        try {
            var data = await api("/auth/login", {
                method: "POST",
                body: {
                    email: $("#login-email").value.trim(),
                    password: $("#login-password").value,
                },
            });
            currentUser = { user_id: data.user_id, name: data.name };
            updateNav();
            toast("Welcome back, " + data.name + "!", "success");
            navigate("/dashboard");
        } catch (err) {
            errEl.textContent = err.message || "Login failed.";
        }
    });

    /* Logout */
    $("#btn-logout").addEventListener("click", async function () {
        try { await api("/auth/logout", { method: "POST" }); } catch (e) {}
        currentUser = null;
        updateNav();
        toast("Logged out.", "info");
        navigate("/");
    });

    /* Hamburger */
    $("#hamburger").addEventListener("click", function () {
        $("#nav-links").classList.toggle("open");
    });

    /* ══════════════════════════════════════════════════════════════
       PAGE: HOME
       ══════════════════════════════════════════════════════════════ */
    async function loadHome() {
        try {
            var props = await api("/properties");
            // hero stats
            $("#hero-prop-count").textContent = props.length;
            var totalVal = props.reduce(function (s, p) { return s + p.total_value; }, 0);
            $("#hero-total-value").textContent = money(totalVal);
            // featured grid
            var html = "";
            props.slice(0, 3).forEach(function (p, i) { html += propCard(p, i); });
            $("#featured-grid").innerHTML = html;
        } catch (e) {
            $("#featured-grid").innerHTML = '<p class="text-muted">Failed to load properties.</p>';
        }
    }

    /* ══════════════════════════════════════════════════════════════
       PAGE: ALL PROPERTIES
       ══════════════════════════════════════════════════════════════ */
    async function loadAllProperties() {
        var grid = $("#all-properties-grid");
        grid.innerHTML = '<div class="spinner"></div>';
        try {
            var props = await api("/properties");
            var html = "";
            props.forEach(function (p, i) { html += propCard(p, i); });
            grid.innerHTML = html || '<p class="text-muted">No properties available.</p>';
        } catch (e) {
            grid.innerHTML = '<p class="text-muted">Failed to load properties.</p>';
        }
    }

    /* ══════════════════════════════════════════════════════════════
       PAGE: PROPERTY DETAIL
       ══════════════════════════════════════════════════════════════ */
    var currentPropertyId = null;
    var appreciationChart = null;

    async function loadPropertyDetail(pid) {
        currentPropertyId = pid;
        try {
            var p = await api("/properties/" + pid);
            // image
            $("#detail-img").innerHTML = houseSvg(pid.charCodeAt(pid.length - 1) % 3);
            // text
            $("#detail-address").textContent = p.address;
            $("#detail-desc").textContent = p.description;

            var funded = p.total_pooled_capital / p.total_value;
            var remaining = p.total_value - p.total_pooled_capital;
            $("#detail-progress").style.width = (funded * 100) + "%";
            $("#detail-funded-label").textContent = (funded * 100).toFixed(1) + "% funded (" + money(p.total_pooled_capital) + ")";
            $("#detail-remaining-label").textContent = money(remaining) + " remaining";

            // metrics (now with appreciation)
            var marketVal = p.current_market_value || p.total_value;
            var appSign = p.appreciation >= 0 ? "+" : "";
            $("#detail-metrics").innerHTML =
                metricHtml("Purchase Value", money(p.total_value)) +
                metricHtml("Market Value", money(marketVal)) +
                metricHtml("Appreciation", appSign + money(Math.abs(p.appreciation || 0)) + " (" + (p.appreciation_pct || 0) + "%)") +
                metricHtml("Monthly Income", money(p.rental_income)) +
                metricHtml("Annual Return", p.expected_annual_return + "%") +
                metricHtml("Investors", p.investors ? p.investors.length : 0);

            // Appreciation stats + chart
            var appStats = $("#detail-appreciation-stats");
            if (p.appreciation != null) {
                var appColor = p.appreciation >= 0 ? "var(--success)" : "var(--danger)";
                appStats.innerHTML =
                    '<div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:8px;">' +
                    '<div><span class="text-muted" style="font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;">Current Market Value</span>' +
                    '<div style="font-family:var(--font-mono);font-size:1.25rem;font-weight:700;">' + money(marketVal) + '</div></div>' +
                    '<div><span class="text-muted" style="font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;">Total Appreciation</span>' +
                    '<div style="font-family:var(--font-mono);font-size:1.25rem;font-weight:700;color:' + appColor + ';">' + appSign + money(Math.abs(p.appreciation)) + ' (' + p.appreciation_pct + '%)</div></div>' +
                    '</div>';
            } else {
                appStats.innerHTML = '';
            }

            renderAppreciationChart(p.valuation_history || []);

            // investors list
            var invDiv = $("#detail-investors");
            if (p.investors && p.investors.length > 0) {
                var rows = "";
                p.investors.forEach(function (inv) {
                    rows += '<div class="investor-row">' +
                        '<span class="investor-name">' + esc(inv.name) + '</span>' +
                        '<span><span class="text-muted">' + money(inv.amount) + '</span> &middot; <span class="investor-share">' + pct(inv.ownership_share) + '</span></span>' +
                        '</div>';
                });
                invDiv.innerHTML = rows;
            } else {
                invDiv.innerHTML = '<p class="text-muted">No investors yet. Be the first!</p>';
            }

            // Distribution history
            var distDiv = $("#detail-dist-history");
            if (p.distribution_history && p.distribution_history.length > 0) {
                var dRows = '<table class="tx-table"><thead><tr><th>Date</th><th>Recipient</th><th style="text-align:right;">Amount</th></tr></thead><tbody>';
                p.distribution_history.forEach(function (d) {
                    dRows += '<tr>' +
                        '<td>' + shortDate(d.timestamp) + '</td>' +
                        '<td>' + esc(d.user_name) + '</td>' +
                        '<td style="text-align:right;font-family:var(--font-mono);font-weight:600;color:var(--success);">+' + moneyDecimal(d.amount) + '</td>' +
                        '</tr>';
                });
                dRows += '</tbody></table>';
                distDiv.innerHTML = dRows;
            } else {
                distDiv.innerHTML = '<p class="text-muted">No distributions have been made yet.</p>';
            }

            // invest sidebar
            if (currentUser) {
                $("#invest-auth-msg").classList.add("hidden");
                $("#form-invest").classList.remove("hidden");
                $("#invest-summary").innerHTML = "Remaining capacity: <strong>" + money(remaining) + "</strong>";
            } else {
                $("#invest-auth-msg").classList.remove("hidden");
                $("#form-invest").classList.add("hidden");
                $("#invest-summary").innerHTML = "";
            }
            $("#invest-error").textContent = "";
            $("#invest-amount").value = "";

        } catch (e) {
            $("#detail-address").textContent = "Property not found";
            $("#detail-desc").textContent = e.message || "";
        }
    }

    function renderAppreciationChart(valuations) {
        var canvas = $("#appreciation-chart");
        if (appreciationChart) { appreciationChart.destroy(); appreciationChart = null; }
        if (!valuations || valuations.length === 0) {
            canvas.style.display = "none";
            return;
        }
        canvas.style.display = "block";
        var labels = valuations.map(function (v) { return shortDate(v.date); });
        var values = valuations.map(function (v) { return v.market_value; });

        appreciationChart = new Chart(canvas, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "Market Value",
                    data: values,
                    borderColor: "#14B8A6",
                    backgroundColor: "rgba(20,184,166,.12)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 5,
                    pointBackgroundColor: "#14B8A6",
                    pointBorderColor: "#1A1A2E",
                    pointBorderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: "#64748B", font: { size: 11 } }, grid: { color: "rgba(255,255,255,.04)" } },
                    y: {
                        ticks: { color: "#64748B", callback: function (v) { return "$" + (v / 1000).toFixed(0) + "k"; } },
                        grid: { color: "rgba(255,255,255,.04)" },
                    },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#22223A", titleColor: "#F1F5F9", bodyColor: "#94A3B8",
                        borderColor: "rgba(255,255,255,.1)", borderWidth: 1,
                        callbacks: { label: function (ctx) { return "$" + ctx.parsed.y.toLocaleString(); } },
                    },
                },
            },
        });
    }

    function metricHtml(label, value) {
        return '<div class="detail-metric">' +
            '<div class="label">' + label + '</div>' +
            '<div class="value">' + value + '</div></div>';
    }

    /* Invest form */
    $("#form-invest").addEventListener("submit", async function (e) {
        e.preventDefault();
        var errEl = $("#invest-error");
        errEl.textContent = "";
        var amt = parseFloat($("#invest-amount").value);
        if (!amt || amt <= 0) { errEl.textContent = "Enter a valid amount."; return; }
        try {
            await api("/investments", {
                method: "POST",
                body: { property_id: currentPropertyId, amount: amt },
            });
            toast("Investment of " + moneyDecimal(amt) + " confirmed!", "success");
            loadPropertyDetail(currentPropertyId);
        } catch (err) {
            errEl.textContent = err.message || "Investment failed.";
        }
    });

    /* ══════════════════════════════════════════════════════════════
       PAGE: DASHBOARD
       ══════════════════════════════════════════════════════════════ */
    var performanceChart = null;

    async function loadDashboard() {
        if (!currentUser) return;
        try {
            var data = await api("/users/" + currentUser.user_id + "/portfolio");
            $("#dash-greeting").textContent = "Welcome back, " + data.user_name + "!";
            $("#dash-total-invested").textContent = money(data.total_invested);
            $("#dash-annual-income").textContent = money(data.total_estimated_annual);
            $("#dash-total-distributions").textContent = money(data.total_distributions);
            $("#dash-prop-count").textContent = data.holdings.length;

            // Appreciation
            var appEl = $("#dash-appreciation");
            appEl.textContent = (data.total_appreciation >= 0 ? "+" : "") + money(data.total_appreciation);
            appEl.style.color = data.total_appreciation >= 0 ? "var(--success)" : "var(--danger)";

            // ROI
            var roiEl = $("#dash-roi");
            roiEl.textContent = (data.roi_pct >= 0 ? "+" : "") + data.roi_pct + "%";
            roiEl.style.color = data.roi_pct >= 0 ? "var(--teal-light)" : "var(--danger)";

            // Portfolio allocation chart
            renderPortfolioChart(data.holdings);

            // Performance over time chart
            renderPerformanceChart(data.performance_timeline);

            // Holdings grid (now with appreciation)
            var hGrid = $("#holdings-grid");
            if (data.holdings.length === 0) {
                hGrid.innerHTML = '<p class="text-muted">No holdings yet. <a href="/properties-page" data-link>Browse properties</a> to start investing.</p>';
            } else {
                var hHtml = "";
                data.holdings.forEach(function (h) {
                    var appSign = h.user_appreciation >= 0 ? "+" : "";
                    var appColor = h.user_appreciation >= 0 ? "var(--success)" : "var(--danger)";
                    hHtml += '<div class="card holding-card">' +
                        '<div class="address">' + esc(h.address) + '</div>' +
                        '<div class="holding-stats">' +
                        '<div><div class="holding-stat-label">Invested</div><div class="holding-stat-value">' + money(h.amount_invested) + '</div></div>' +
                        '<div><div class="holding-stat-label">Ownership</div><div class="holding-stat-value text-teal">' + pct(h.ownership_share) + '</div></div>' +
                        '<div><div class="holding-stat-label">Est. Annual</div><div class="holding-stat-value">' + money(h.estimated_annual_return) + '</div></div>' +
                        '<div><div class="holding-stat-label">Market Value</div><div class="holding-stat-value">' + money(h.user_market_share) + '</div></div>' +
                        '<div><div class="holding-stat-label">Appreciation</div><div class="holding-stat-value" style="color:' + appColor + '">' + appSign + money(Math.abs(h.user_appreciation)) + '</div></div>' +
                        '</div></div>';
                });
                hGrid.innerHTML = hHtml;
            }

            // Transactions
            var tbody = $("#tx-tbody");
            if (data.transactions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-muted" style="text-align:center;">No transactions yet.</td></tr>';
            } else {
                var tHtml = "";
                data.transactions.forEach(function (tx) {
                    var badge = tx.type === "invest"
                        ? '<span class="badge badge-teal">Invest</span>'
                        : '<span class="badge badge-success">Payout</span>';
                    tHtml += '<tr>' +
                        '<td>' + shortDate(tx.timestamp) + '</td>' +
                        '<td>' + badge + '</td>' +
                        '<td>' + esc(tx.address) + '</td>' +
                        '<td style="text-align:right;font-family:var(--font-mono);font-weight:600;">' +
                        (tx.type === "distribute" ? "+" : "-") + moneyDecimal(tx.amount) + '</td></tr>';
                });
                tbody.innerHTML = tHtml;
            }
        } catch (e) {
            toast("Failed to load portfolio: " + (e.message || ""), "error");
        }
    }

    function renderPerformanceChart(timeline) {
        var canvas = $("#performance-chart");
        var emptyMsg = $("#perf-chart-empty");
        if (performanceChart) { performanceChart.destroy(); performanceChart = null; }

        if (!timeline || timeline.length === 0) {
            canvas.style.display = "none";
            emptyMsg.classList.remove("hidden");
            return;
        }
        canvas.style.display = "block";
        emptyMsg.classList.add("hidden");

        var labels = timeline.map(function (t) { return shortDate(t.date); });
        var invested = timeline.map(function (t) { return t.total_invested; });
        var earned = timeline.map(function (t) { return t.total_earned; });

        performanceChart = new Chart(canvas, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Total Invested",
                        data: invested,
                        borderColor: "#0D7377",
                        backgroundColor: "rgba(13,115,119,.15)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: "#0D7377",
                    },
                    {
                        label: "Total Earned",
                        data: earned,
                        borderColor: "#22C55E",
                        backgroundColor: "rgba(34,197,94,.1)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: "#22C55E",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        ticks: { color: "#64748B", font: { size: 11 } },
                        grid: { color: "rgba(255,255,255,.04)" },
                    },
                    y: {
                        ticks: {
                            color: "#64748B",
                            callback: function (v) { return "$" + v.toLocaleString(); },
                        },
                        grid: { color: "rgba(255,255,255,.04)" },
                    },
                },
                plugins: {
                    legend: {
                        labels: { color: "#94A3B8", font: { family: "'DM Sans', sans-serif", size: 12 }, usePointStyle: true },
                    },
                    tooltip: {
                        backgroundColor: "#22223A",
                        titleColor: "#F1F5F9",
                        bodyColor: "#94A3B8",
                        borderColor: "rgba(255,255,255,.1)",
                        borderWidth: 1,
                        callbacks: {
                            label: function (ctx) { return " " + ctx.dataset.label + ": $" + ctx.parsed.y.toLocaleString(); },
                        },
                    },
                },
            },
        });
    }

    function renderPortfolioChart(holdings) {
        var canvas = $("#portfolio-chart");
        var emptyMsg = $("#chart-empty");
        if (portfolioChart) { portfolioChart.destroy(); portfolioChart = null; }

        if (!holdings || holdings.length === 0) {
            canvas.style.display = "none";
            emptyMsg.classList.remove("hidden");
            return;
        }
        canvas.style.display = "block";
        emptyMsg.classList.add("hidden");

        var labels = holdings.map(function (h) {
            var parts = h.address.split(",");
            return parts[0].length > 25 ? parts[0].substring(0, 25) + "…" : parts[0];
        });
        var amounts = holdings.map(function (h) { return h.amount_invested; });
        var bgColors = ["#0D7377", "#14B8A6", "#A7F3D0", "#065F46", "#F59E0B", "#EF4444"];

        portfolioChart = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: amounts,
                    backgroundColor: bgColors.slice(0, amounts.length),
                    borderColor: "rgba(26,26,46,.9)",
                    borderWidth: 3,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#94A3B8",
                            font: { family: "'DM Sans', sans-serif", size: 12 },
                            padding: 16,
                            usePointStyle: true,
                            pointStyleWidth: 10,
                        },
                    },
                    tooltip: {
                        backgroundColor: "#22223A",
                        titleColor: "#F1F5F9",
                        bodyColor: "#94A3B8",
                        borderColor: "rgba(255,255,255,.1)",
                        borderWidth: 1,
                        callbacks: {
                            label: function (ctx) {
                                return " " + ctx.label + ": $" + ctx.parsed.toLocaleString();
                            },
                        },
                    },
                },
            },
        });
    }

    /* ══════════════════════════════════════════════════════════════
       PAGE: ADMIN
       ══════════════════════════════════════════════════════════════ */
    async function loadAdmin() {
        var list = $("#admin-properties-list");
        var valList = $("#admin-valuations-list");
        list.innerHTML = '<div class="spinner"></div>';
        valList.innerHTML = '<div class="spinner"></div>';
        try {
            var props = await api("/properties");

            // Distribution section
            var html = "";
            props.forEach(function (p) {
                html += '<div class="admin-prop-card">' +
                    '<div class="admin-prop-info">' +
                    '<div class="addr">' + esc(p.address) + '</div>' +
                    '<div class="meta">Monthly income: ' + money(p.rental_income) + ' &middot; Pooled: ' + money(p.total_pooled_capital) + '</div>' +
                    '</div>' +
                    '<div class="admin-actions">' +
                    '<input type="number" placeholder="' + p.rental_income + '" id="admin-amt-' + p._id + '" min="0" step="any">' +
                    '<button class="btn btn-primary btn-sm" onclick="FRIP.distribute(\'' + p._id + '\')">Distribute</button>' +
                    '</div></div>';
            });
            list.innerHTML = html || '<p class="text-muted">No properties.</p>';

            // Valuation section
            var vHtml = "";
            props.forEach(function (p) {
                var marketVal = p.current_market_value || p.total_value;
                var appAmt = marketVal - p.total_value;
                var appPct = p.total_value ? ((appAmt / p.total_value) * 100).toFixed(1) : "0.0";
                var appColor = appAmt >= 0 ? "var(--success)" : "var(--danger)";
                vHtml += '<div class="admin-prop-card">' +
                    '<div class="admin-prop-info">' +
                    '<div class="addr">' + esc(p.address) + '</div>' +
                    '<div class="meta">Purchase: ' + money(p.total_value) + ' &middot; Current: ' + money(marketVal) +
                    ' &middot; <span style="color:' + appColor + '">' + (appAmt >= 0 ? "+" : "") + appPct + '%</span></div>' +
                    '</div>' +
                    '<div class="admin-actions">' +
                    '<input type="number" placeholder="' + marketVal + '" id="admin-val-' + p._id + '" min="0" step="any">' +
                    '<button class="btn btn-secondary btn-sm" onclick="FRIP.updateValuation(\'' + p._id + '\')">Update</button>' +
                    '</div></div>';
            });
            valList.innerHTML = vHtml || '<p class="text-muted">No properties.</p>';
        } catch (e) {
            list.innerHTML = '<p class="text-muted">Failed to load.</p>';
            valList.innerHTML = '<p class="text-muted">Failed to load.</p>';
        }
    }

    async function distribute(propId) {
        var input = document.getElementById("admin-amt-" + propId);
        var amt = input ? parseFloat(input.value) : null;
        var body = {};
        if (amt && amt > 0) body.rental_income = amt;
        try {
            var data = await api("/distributions/" + propId, { method: "POST", body: body });
            var total = data.payouts.reduce(function (s, p) { return s + p.payout; }, 0);
            toast("Distributed " + moneyDecimal(total) + " to " + data.payouts.length + " investor(s).", "success");
        } catch (err) {
            toast(err.message || "Distribution failed.", "error");
        }
    }

    async function updateValuation(propId) {
        var input = document.getElementById("admin-val-" + propId);
        var val = input ? parseFloat(input.value) : null;
        if (!val || val <= 0) {
            toast("Enter a valid market value.", "error");
            return;
        }
        try {
            var data = await api("/properties/" + propId + "/valuation", {
                method: "POST",
                body: { market_value: val },
            });
            toast("Valuation updated: " + money(data.new_value) + " (" + (data.change_pct >= 0 ? "+" : "") + data.change_pct + "%)", "success");
            loadAdmin();
        } catch (err) {
            toast(err.message || "Valuation update failed.", "error");
        }
    }

    /* ══════════════════════════════════════════════════════════════
       INIT
       ══════════════════════════════════════════════════════════════ */
    async function init() {
        await checkAuth();
        navigate(location.pathname, false);
    }

    /* expose for inline onclick */
    window.FRIP = { distribute: distribute, updateValuation: updateValuation };

    init();

})();