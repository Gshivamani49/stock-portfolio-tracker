import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Pro Stock Portfolio Dashboard")

# ---------------------------------------------------------
# BACKEND: RICH STOCK DATABASE & ANALYTICS ENGINE
# ---------------------------------------------------------

STOCKS_DB = {
    "AAPL": {"name": "Apple Inc.", "price": 224.23, "sector": "Technology", "change_24h": 1.45},
    "NVDA": {"name": "NVIDIA Corp.", "price": 128.15, "sector": "Semiconductors", "change_24h": 3.82},
    "MSFT": {"name": "Microsoft Corp.", "price": 448.30, "sector": "Technology", "change_24h": 0.92},
    "TSLA": {"name": "Tesla Inc.", "price": 254.10, "sector": "Automotive", "change_24h": -2.15},
    "AMZN": {"name": "Amazon.com Inc.", "price": 186.50, "sector": "E-Commerce", "change_24h": 2.10},
    "GOOGL": {"name": "Alphabet Inc.", "price": 178.40, "sector": "Communication", "change_24h": -0.45},
    "BTC": {"name": "Bitcoin (Crypto)", "price": 64250.00, "sector": "Cryptocurrency", "change_24h": 4.12}
}

class PortfolioItemInput(BaseModel):
    symbol: str
    quantity: float

class PortfolioRequest(BaseModel):
    items: List[PortfolioItemInput]

@app.get("/api/stocks")
def get_stocks():
    """Returns available tickers with live prices and sector metadata."""
    return STOCKS_DB

@app.post("/api/analyze")
def analyze_portfolio(data: PortfolioRequest):
    """Calculates allocation breakdown, total value, top holding, and sector weights."""
    if not data.items:
        return {"summary": [], "total_value": 0, "top_holding": "N/A", "sector_allocation": {}}

    summary = []
    total_value = 0.0
    sector_totals: Dict[str, float] = {}

    # First pass: compute subtotals
    for item in data.items:
        symbol = item.symbol.upper()
        if symbol not in STOCKS_DB:
            raise HTTPException(status_code=400, detail=f"Ticker '{symbol}' not recognized.")
        if item.quantity <= 0:
            continue

        info = STOCKS_DB[symbol]
        subtotal = item.quantity * info["price"]
        total_value += subtotal

        sector = info["sector"]
        sector_totals[sector] = sector_totals.get(sector, 0.0) + subtotal

        summary.append({
            "symbol": symbol,
            "name": info["name"],
            "quantity": item.quantity,
            "price": info["price"],
            "subtotal": round(subtotal, 2),
            "sector": sector,
            "change_24h": info["change_24h"],
            "weight_pct": 0  # Will calculate in second pass
        })

    # Second pass: compute allocation percentages
    top_holding_name = "N/A"
    max_subtotal = -1

    for s in summary:
        s["weight_pct"] = round((s["subtotal"] / total_value) * 100, 2) if total_value > 0 else 0
        if s["subtotal"] > max_subtotal:
            max_subtotal = s["subtotal"]
            top_holding_name = f"{s['symbol']} ({s['weight_pct']}%)"

    return {
        "summary": summary,
        "total_value": round(total_value, 2),
        "top_holding": top_holding_name,
        "total_assets": len(summary),
        "sector_allocation": {k: round((v / total_value) * 100, 1) for k, v in sector_totals.items()} if total_value > 0 else {}
    }

# ---------------------------------------------------------
# FRONTEND: FINTECH DASHBOARD (Tailwind + Chart.js)
# ---------------------------------------------------------

HTML_UI = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise Portfolio Tracker</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- FontAwesome CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        darkbg: '#090d16',
                        cardbg: '#131b2e',
                        bordercolor: '#1e293b',
                        accent: '#38bdf8'
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-darkbg text-slate-100 font-sans min-h-screen">

    <!-- Header -->
    <header class="border-b border-bordercolor bg-cardbg/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex justify-between items-center">
        <div class="flex items-center space-x-3">
            <div class="p-2 bg-sky-500/10 text-sky-400 rounded-lg border border-sky-500/20">
                <i class="fa-solid fa-chart-pie text-xl"></i>
            </div>
            <div>
                <h1 class="text-xl font-bold bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">Apex Analytics</h1>
                <p class="text-xs text-slate-400">Stock & Asset Portfolio Tracker</p>
            </div>
        </div>
        <div class="flex items-center space-x-4">
            <span class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Markets Live
            </span>
            <button onclick="loadSampleData()" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-md transition">
                ⚡ Load Demo Data
            </button>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-8 space-y-6">

        <!-- Stat Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-cardbg p-6 rounded-xl border border-bordercolor shadow-lg relative overflow-hidden">
                <div class="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Net Value</div>
                <div class="text-3xl font-extrabold text-white mt-2" id="statTotal">$0.00</div>
                <div class="text-xs text-slate-500 mt-1">Real-time aggregate portfolio evaluation</div>
                <div class="absolute -right-2 -bottom-2 opacity-5 text-sky-400 text-7xl"><i class="fa-solid fa-wallet"></i></div>
            </div>

            <div class="bg-cardbg p-6 rounded-xl border border-bordercolor shadow-lg relative overflow-hidden">
                <div class="text-xs font-medium text-slate-400 uppercase tracking-wider">Top Holding Allocation</div>
                <div class="text-2xl font-bold text-sky-400 mt-2" id="statTop">N/A</div>
                <div class="text-xs text-slate-500 mt-1">Largest position in your portfolio</div>
                <div class="absolute -right-2 -bottom-2 opacity-5 text-sky-400 text-7xl"><i class="fa-solid fa-crown"></i></div>
            </div>

            <div class="bg-cardbg p-6 rounded-xl border border-bordercolor shadow-lg relative overflow-hidden">
                <div class="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Asset Positions</div>
                <div class="text-3xl font-extrabold text-indigo-400 mt-2" id="statAssets">0</div>
                <div class="text-xs text-slate-500 mt-1">Distinct stock tickers tracked</div>
                <div class="absolute -right-2 -bottom-2 opacity-5 text-indigo-400 text-7xl"><i class="fa-solid fa-layer-group"></i></div>
            </div>
        </div>

        <!-- Interactive Grid Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

            <!-- Left 2 Columns: Add Form & Table -->
            <div class="lg:col-span-2 space-y-6">
                
                <!-- Input Card -->
                <div class="bg-cardbg p-6 rounded-xl border border-bordercolor shadow-lg">
                    <h2 class="text-base font-semibold text-slate-200 mb-4 flex items-center gap-2">
                        <i class="fa-solid fa-plus-circle text-sky-400"></i> Add Position
                    </h2>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <select id="stockSelect" class="bg-darkbg border border-bordercolor text-slate-200 text-sm rounded-lg p-3 focus:outline-none focus:border-sky-500">
                            <option value="">Fetching stocks...</option>
                        </select>
                        <input type="number" id="quantityInput" placeholder="Quantity (e.g. 10)" min="0.01" step="any" class="bg-darkbg border border-bordercolor text-slate-200 text-sm rounded-lg p-3 focus:outline-none focus:border-sky-500">
                        <button onclick="addStock()" class="bg-sky-500 hover:bg-sky-600 text-slate-950 font-bold py-3 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2 text-sm">
                            <i class="fa-solid fa-plus"></i> Add to Portfolio
                        </button>
                    </div>
                </div>

                <!-- Table Card -->
                <div class="bg-cardbg p-6 rounded-xl border border-bordercolor shadow-lg overflow-hidden">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-base font-semibold text-slate-200 flex items-center gap-2">
                            <i class="fa-solid fa-list-check text-sky-400"></i> Holdings Breakdown
                        </h2>
                        <button onclick="exportCSV()" class="text-xs bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 px-3 py-1.5 rounded-md flex items-center gap-1">
                            <i class="fa-solid fa-download"></i> Export CSV
                        </button>
                    </div>

                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm text-slate-300">
                            <thead class="bg-darkbg/50 text-slate-400 text-xs uppercase border-b border-bordercolor">
                                <tr>
                                    <th class="py-3 px-4">Asset</th>
                                    <th class="py-3 px-4">Price</th>
                                    <th class="py-3 px-4">Shares</th>
                                    <th class="py-3 px-4">Total Value</th>
                                    <th class="py-3 px-4">Weight</th>
                                    <th class="py-3 px-4 text-center">Action</th>
                                </tr>
                            </thead>
                            <tbody id="portfolioTable">
                                <tr>
                                    <td colspan="6" class="text-center py-8 text-slate-500">No positions open. Select a stock above to begin.</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>

            <!-- Right Column: Visualization Chart -->
            <div class="space-y-6">
                <div class="bg-cardbg p-6 rounded-xl border border-bordercolor shadow-lg flex flex-col justify-between h-full">
                    <div>
                        <h2 class="text-base font-semibold text-slate-200 mb-2 flex items-center gap-2">
                            <i class="fa-solid fa-chart-donut text-indigo-400"></i> Asset Allocation
                        </h2>
                        <p class="text-xs text-slate-400 mb-6">Percentage breakdown of total capital distribution.</p>
                    </div>

                    <div class="relative flex items-center justify-center p-4">
                        <canvas id="allocationChart" class="max-h-[260px]"></canvas>
                    </div>

                    <div id="sectorLegend" class="mt-6 pt-4 border-t border-bordercolor text-xs text-slate-400 space-y-2">
                        <!-- Sector dynamic badges -->
                    </div>
                </div>
            </div>

        </div>
    </main>

    <script>
        let myChart = null;
        let portfolioItems = JSON.parse(localStorage.getItem("portfolio_items") || "[]");

        async function init() {
            await fetchStocks();
            await refreshPortfolio();
        }

        async function fetchStocks() {
            try {
                const res = await fetch("/api/stocks");
                const stocks = await res.json();
                const select = document.getElementById("stockSelect");
                select.innerHTML = '<option value="">-- Choose Stock Ticker --</option>';
                
                for (const [symbol, info] of Object.entries(stocks)) {
                    select.innerHTML += `<option value="${symbol}">${symbol} - ${info.name} ($${info.price})</option>`;
                }
            } catch (err) {
                console.error("Failed to load stocks:", err);
            }
        }

        function saveLocal() {
            localStorage.setItem("portfolio_items", JSON.stringify(portfolioItems));
        }

        function addStock() {
            const symbol = document.getElementById("stockSelect").value;
            const quantity = parseFloat(document.getElementById("quantityInput").value);

            if (!symbol || isNaN(quantity) || quantity <= 0) {
                alert("Please select a ticker and specify a valid positive share amount.");
                return;
            }

            const existing = portfolioItems.find(i => i.symbol === symbol);
            if (existing) {
                existing.quantity += quantity;
            } else {
                portfolioItems.push({ symbol, quantity });
            }

            document.getElementById("quantityInput").value = "";
            saveLocal();
            refreshPortfolio();
        }

        function removeStock(symbol) {
            portfolioItems = portfolioItems.filter(i => i.symbol !== symbol);
            saveLocal();
            refreshPortfolio();
        }

        function loadSampleData() {
            portfolioItems = [
                { symbol: "NVDA", quantity: 15 },
                { symbol: "AAPL", quantity: 10 },
                { symbol: "MSFT", quantity: 5 },
                { symbol: "BTC", quantity: 0.1 }
            ];
            saveLocal();
            refreshPortfolio();
        }

        async function refreshPortfolio() {
            if (portfolioItems.length === 0) {
                document.getElementById("portfolioTable").innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-500">No positions open. Select a stock above to begin.</td></tr>`;
                document.getElementById("statTotal").innerText = "$0.00";
                document.getElementById("statTop").innerText = "N/A";
                document.getElementById("statAssets").innerText = "0";
                updateChart([], []);
                document.getElementById("sectorLegend").innerHTML = "";
                return;
            }

            try {
                const res = await fetch("/api/analyze", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ items: portfolioItems })
                });
                const data = await res.json();

                // Update Stats
                document.getElementById("statTotal").innerText = `$${data.total_value.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
                document.getElementById("statTop").innerText = data.top_holding;
                document.getElementById("statAssets").innerText = data.total_assets;

                // Update Table
                const tbody = document.getElementById("portfolioTable");
                tbody.innerHTML = "";
                data.summary.forEach(item => {
                    const isPositive = item.change_24h >= 0;
                    tbody.innerHTML += `
                        <tr class="border-b border-bordercolor/50 hover:bg-slate-800/30 transition">
                            <td class="py-3 px-4">
                                <div class="font-bold text-white">${item.symbol}</div>
                                <div class="text-xs text-slate-400">${item.name}</div>
                            </td>
                            <td class="py-3 px-4 font-mono">$${item.price.toFixed(2)}</td>
                            <td class="py-3 px-4">${item.quantity}</td>
                            <td class="py-3 px-4 font-mono font-semibold text-slate-100">$${item.subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                            <td class="py-3 px-4">
                                <span class="text-xs px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 font-mono font-medium">${item.weight_pct}%</span>
                            </td>
                            <td class="py-3 px-4 text-center">
                                <button onclick="removeStock('${item.symbol}')" class="text-slate-500 hover:text-red-400 transition">
                                    <i class="fa-solid fa-trash-can"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                });

                // Update Chart
                const labels = data.summary.map(i => i.symbol);
                const values = data.summary.map(i => i.subtotal);
                updateChart(labels, values);

                // Update Sector Allocation Legend
                let sectorHTML = '<div class="font-semibold text-slate-300 mb-2">Sector Breakdown</div>';
                for (const [sec, pct] of Object.entries(data.sector_allocation)) {
                    sectorHTML += `
                        <div class="flex justify-between items-center text-xs">
                            <span class="text-slate-400">${sec}</span>
                            <span class="font-mono text-slate-200 font-medium">${pct}%</span>
                        </div>
                    `;
                }
                document.getElementById("sectorLegend").innerHTML = sectorHTML;

            } catch (err) {
                console.error("Failed analysis:", err);
            }
        }

        function updateChart(labels, values) {
            const ctx = document.getElementById('allocationChart').getContext('2d');
            if (myChart) myChart.destroy();

            if (labels.length === 0) return;

            myChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: [
                            '#38bdf8', '#818cf8', '#34d399', '#f43f5e', '#fbbf24', '#a78bfa', '#ec4899'
                        ],
                        borderWidth: 2,
                        borderColor: '#131b2e'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#94a3b8', font: { size: 11 } }
                        }
                    },
                    cutout: '68%'
                }
            });
        }

        function exportCSV() {
            if (portfolioItems.length === 0) return alert("Portfolio is empty.");
            let csv = "Symbol,Quantity\\n";
            portfolioItems.forEach(i => csv += `${i.symbol},${i.quantity}\\n`);
            const blob = new Blob([csv], { type: 'text/csv' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'portfolio.csv';
            a.click();
        }

        window.onload = init;
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    return HTML_UI

if __name__ == "__main__":
    print("==========================================================")
    print("🚀 APEX ANALYTICS - PRO PORTFOLIO DASHBOARD IS ONLINE")
    print("👉 Open your browser at: http://127.0.0.1:8000")
    print("==========================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000)