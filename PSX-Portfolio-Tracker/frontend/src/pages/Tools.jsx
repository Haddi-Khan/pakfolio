import { useState, useCallback } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { fmt } from "../utils/format";
import {
  TrendingUp, Calculator, Repeat, BarChart2, DollarSign, Star, ChevronRight,
  ArrowLeft, Info,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  BarChart, Bar,
} from "recharts";

// ─── Shared helpers ────────────────────────────────────────────────────────
function InputField({ label, value, onChange, unit, min = 0, step = 1, hint }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-black uppercase tracking-widest text-muted">{label}</label>
      <div className="relative">
        <input
          type="number"
          value={value}
          onChange={e => onChange(e.target.value)}
          min={min}
          step={step}
          className="w-full bg-white/5 border border-border rounded-xl px-4 py-3 text-white text-sm font-semibold focus:outline-none focus:border-accent/60 focus:bg-white/8 transition-all pr-16"
        />
        {unit && (
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-black text-muted uppercase tracking-widest">
            {unit}
          </span>
        )}
      </div>
      {hint && <p className="text-[10px] text-muted/60">{hint}</p>}
    </div>
  );
}

function ResultCard({ label, value, highlight, sub }) {
  return (
    <div className={`rounded-xl p-4 border ${highlight ? "bg-accent/10 border-accent/30" : "bg-white/[0.03] border-border"}`}>
      <div className="text-[9px] font-black uppercase tracking-widest text-muted mb-1">{label}</div>
      <div className={`text-xl font-black mono ${highlight ? "text-accent" : "text-white"}`}>{value}</div>
      {sub && <div className="text-[10px] text-muted/60 mt-0.5">{sub}</div>}
    </div>
  );
}

function CalcButton({ onClick, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full bg-accent hover:bg-accent/90 text-white font-black text-[11px] uppercase tracking-widest py-3.5 rounded-xl transition-all shadow-lg shadow-accent/20 active:scale-[0.98]"
    >
      {loading ? "Calculating…" : "Calculate"}
    </button>
  );
}

function InfoBox({ title, children }) {
  return (
    <div className="rounded-xl bg-white/[0.02] border border-border p-5 space-y-2">
      <div className="flex items-center gap-2 text-accent">
        <Info size={14} />
        <span className="text-[11px] font-black uppercase tracking-widest">{title}</span>
      </div>
      <div className="text-[12px] text-muted/80 leading-relaxed">{children}</div>
    </div>
  );
}

// ─── 1. SIP Calculator ────────────────────────────────────────────────────
function SIPCalculator() {
  const [monthly, setMonthly] = useState(10000);
  const [rate, setRate] = useState(12);
  const [years, setYears] = useState(10);
  const [result, setResult] = useState(null);

  const calculate = useCallback(() => {
    const p = parseFloat(monthly) || 0;
    const r = (parseFloat(rate) || 0) / 100 / 12;
    const n = (parseFloat(years) || 0) * 12;
    if (!p || !n) { setResult(null); return; }
    const fv = r > 0
      ? p * (((Math.pow(1 + r, n) - 1) / r) * (1 + r))
      : p * n;
    const deposited = p * n;
    const earnings = fv - deposited;
    // Build year-by-year chart data
    const chartData = [];
    for (let y = 1; y <= Math.min(parseFloat(years) || 0, 30); y++) {
      const nn = y * 12;
      const val = r > 0
        ? p * (((Math.pow(1 + r, nn) - 1) / r) * (1 + r))
        : p * nn;
      chartData.push({ year: `Y${y}`, deposited: Math.round(p * nn), value: Math.round(val) });
    }
    setResult({ fv, deposited, earnings, chartData });
  }, [monthly, rate, years]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <InputField label="Monthly Investment" value={monthly} onChange={setMonthly} unit="PKR" min={1} />
        <InputField label="Annual Return Rate" value={rate} onChange={setRate} unit="%" min={0} step={0.1} />
        <InputField label="Duration" value={years} onChange={setYears} unit="Years" min={1} />
      </div>
      <CalcButton onClick={calculate} />

      {result && (
        <div className="space-y-5 animate-in fade-in duration-300">
          <div className="grid grid-cols-3 gap-3">
            <ResultCard label="Total Deposited" value={fmt.pkr(result.deposited)} />
            <ResultCard label="Total Earnings" value={fmt.pkr(result.earnings)} highlight />
            <ResultCard label="Future Value" value={fmt.pkr(result.fv)} sub="At maturity" />
          </div>
          <div className="h-56 rounded-xl overflow-hidden bg-white/[0.02] border border-border p-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={result.chartData} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
                <defs>
                  <linearGradient id="sipGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis dataKey="year" tick={{ fill: "#5A6B82", fontSize: 9, fontWeight: 800 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#5A6B82", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => fmt.compact(v)} width={55} />
                <Tooltip formatter={(v, n) => [fmt.pkr(v), n === "value" ? "Portfolio Value" : "Amount Deposited"]} contentStyle={{ background: "#0d1520", border: "1px solid #1e2d3d", borderRadius: 10, fontSize: 11 }} />
                <Area type="monotone" dataKey="deposited" stroke="#5A6B82" strokeWidth={1} fill="transparent" dot={false} />
                <Area type="monotone" dataKey="value" stroke="var(--color-accent)" strokeWidth={2.5} fill="url(#sipGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <InfoBox title="What is SIP?">
        A Systematic Investment Plan (SIP) lets you invest a fixed amount every month. Your returns compound monthly — meaning your earnings also earn returns, accelerating growth over time. Ideal for disciplined, long-term wealth building on PSX mutual funds or stocks.
        <div className="mt-2 font-mono text-[11px] bg-white/5 rounded-lg p-2">
          FV = P × [((1 + r)ⁿ − 1) / r] × (1 + r) &nbsp;|&nbsp; r = annual rate ÷ 12
        </div>
      </InfoBox>
    </div>
  );
}

// ─── 2. Compounding Calculator ────────────────────────────────────────────
function CompoundingCalculator() {
  const [principal, setPrincipal] = useState(100000);
  const [rate, setRate] = useState(15);
  const [years, setYears] = useState(10);
  const [freq, setFreq] = useState(1); // 1=annual, 12=monthly
  const [result, setResult] = useState(null);

  const calculate = useCallback(() => {
    const p = parseFloat(principal) || 0;
    const r = (parseFloat(rate) || 0) / 100;
    const n = parseFloat(years) || 0;
    const f = parseInt(freq) || 1;
    if (!p || !n) { setResult(null); return; }
    const fv = p * Math.pow(1 + r / f, f * n);
    const profit = fv - p;
    const chartData = [];
    for (let y = 1; y <= Math.min(n, 30); y++) {
      chartData.push({
        year: `Y${y}`,
        value: Math.round(p * Math.pow(1 + r / f, f * y)),
        principal: Math.round(p),
      });
    }
    setResult({ fv, profit, chartData });
  }, [principal, rate, years, freq]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <InputField label="Starting Balance" value={principal} onChange={setPrincipal} unit="PKR" min={1} />
        <InputField label="Annual Growth Rate" value={rate} onChange={setRate} unit="%" min={0} step={0.1} />
        <InputField label="Period" value={years} onChange={setYears} unit="Years" min={1} />
        <div className="space-y-1.5">
          <label className="text-[10px] font-black uppercase tracking-widest text-muted">Compounding Frequency</label>
          <select value={freq} onChange={e => setFreq(e.target.value)} className="w-full bg-white/5 border border-border rounded-xl px-4 py-3 text-white text-sm font-semibold focus:outline-none focus:border-accent/60 transition-all">
            <option value={1}>Annually</option>
            <option value={2}>Semi-annually</option>
            <option value={4}>Quarterly</option>
            <option value={12}>Monthly</option>
          </select>
        </div>
      </div>
      <CalcButton onClick={calculate} />

      {result && (
        <div className="space-y-5 animate-in fade-in duration-300">
          <div className="grid grid-cols-2 gap-3">
            <ResultCard label="Final Amount" value={fmt.pkr(result.fv)} highlight />
            <ResultCard label="Total Profit" value={fmt.pkr(result.profit)} sub={`+${((result.profit / (parseFloat(principal) || 1)) * 100).toFixed(1)}% total return`} />
          </div>
          <div className="h-52 rounded-xl overflow-hidden bg-white/[0.02] border border-border p-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={result.chartData} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
                <defs>
                  <linearGradient id="compGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis dataKey="year" tick={{ fill: "#5A6B82", fontSize: 9, fontWeight: 800 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#5A6B82", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => fmt.compact(v)} width={55} />
                <Tooltip formatter={(v) => [fmt.pkr(v)]} contentStyle={{ background: "#0d1520", border: "1px solid #1e2d3d", borderRadius: 10, fontSize: 11 }} />
                <Area type="monotone" dataKey="principal" stroke="#5A6B82" strokeWidth={1} fill="transparent" dot={false} name="Principal" />
                <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2.5} fill="url(#compGrad)" dot={false} name="Compounded Value" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <InfoBox title="Power of Compounding">
        Compounding means your profits earn profits. PKR 100,000 at 15% for 10 years = PKR 404,555 — over 4× your money. The more frequently it compounds, the faster it grows. Einstein called it "the eighth wonder of the world."
        <div className="mt-2 font-mono text-[11px] bg-white/5 rounded-lg p-2">
          A = P × (1 + r/n)^(n×t)
        </div>
      </InfoBox>
    </div>
  );
}

// ─── 3. CAGR Calculator ───────────────────────────────────────────────────
function CAGRCalculator() {
  const [initial, setInitial] = useState(100000);
  const [final, setFinal] = useState(250000);
  const [years, setYears] = useState(5);
  const [result, setResult] = useState(null);

  const calculate = useCallback(() => {
    const p = parseFloat(initial) || 0;
    const f = parseFloat(final) || 0;
    const n = parseFloat(years) || 0;
    if (!p || !f || !n) { setResult(null); return; }
    const cagr = (Math.pow(f / p, 1 / n) - 1) * 100;
    const absolute = ((f - p) / p) * 100;
    const gains = f - p;
    // Year-by-year projection
    const chartData = [];
    for (let y = 0; y <= n; y++) {
      chartData.push({ year: `Y${y}`, value: Math.round(p * Math.pow(1 + cagr / 100, y)) });
    }
    setResult({ cagr, absolute, gains, initial: p, final: f, chartData });
  }, [initial, final, years]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <InputField label="Initial Investment" value={initial} onChange={setInitial} unit="PKR" min={1} />
        <InputField label="Final Value" value={final} onChange={setFinal} unit="PKR" min={1} />
        <InputField label="Duration" value={years} onChange={setYears} unit="Years" min={1} />
      </div>
      <CalcButton onClick={calculate} />

      {result && (
        <div className="space-y-5 animate-in fade-in duration-300">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <ResultCard label="Initial Invested" value={fmt.pkr(result.initial)} />
            <ResultCard label="Final Value" value={fmt.pkr(result.final)} />
            <ResultCard label="Gains" value={fmt.pkr(result.gains)} highlight />
            <ResultCard label="CAGR" value={`${result.cagr.toFixed(2)}%`} highlight sub={`Absolute: ${result.absolute.toFixed(1)}%`} />
          </div>
          <div className="h-52 rounded-xl overflow-hidden bg-white/[0.02] border border-border p-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={result.chartData} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
                <defs>
                  <linearGradient id="cagrGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis dataKey="year" tick={{ fill: "#5A6B82", fontSize: 9, fontWeight: 800 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#5A6B82", fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => fmt.compact(v)} width={55} />
                <Tooltip formatter={(v) => [fmt.pkr(v), "Projected Value"]} contentStyle={{ background: "#0d1520", border: "1px solid #1e2d3d", borderRadius: 10, fontSize: 11 }} />
                <Area type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2.5} fill="url(#cagrGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <InfoBox title="CAGR vs Absolute Return">
        <strong className="text-white">CAGR</strong> smooths out year-to-year volatility into a single annual growth rate — the rate at which your investment would have grown if it grew steadily every year. <strong className="text-white">Absolute return</strong> is the total % gain regardless of time. CAGR is more useful for comparing investments held for different periods.
        <div className="mt-2 font-mono text-[11px] bg-white/5 rounded-lg p-2">
          CAGR = (Final / Initial)^(1/n) − 1
        </div>
      </InfoBox>
    </div>
  );
}

// ─── 4. ROI Calculator ────────────────────────────────────────────────────
function ROICalculator() {
  const [buyPrice, setBuyPrice] = useState(100);
  const [sellPrice, setSellPrice] = useState(130);
  const [shares, setShares] = useState(500);
  const [buyComm, setBuyComm] = useState(0.12);
  const [sellComm, setSellComm] = useState(0.12);
  const [dividends, setDividends] = useState(0);
  const [result, setResult] = useState(null);

  const calculate = useCallback(() => {
    const bp = parseFloat(buyPrice) || 0;
    const sp = parseFloat(sellPrice) || 0;
    const q = parseFloat(shares) || 0;
    const bc = (parseFloat(buyComm) || 0) / 100;
    const sc = (parseFloat(sellComm) || 0) / 100;
    const div = parseFloat(dividends) || 0;
    if (!bp || !sp || !q) { setResult(null); return; }
    const cost = bp * q * (1 + bc);
    const proceeds = sp * q * (1 - sc) + div * q;
    const netGain = proceeds - cost;
    const roi = (netGain / cost) * 100;
    const capitalGain = (sp - bp) * q;
    setResult({ cost, proceeds, netGain, roi, capitalGain, dividendIncome: div * q });
  }, [buyPrice, sellPrice, shares, buyComm, sellComm, dividends]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <InputField label="Buy Price" value={buyPrice} onChange={setBuyPrice} unit="PKR" min={0.01} step={0.01} />
        <InputField label="Sell Price" value={sellPrice} onChange={setSellPrice} unit="PKR" min={0.01} step={0.01} />
        <InputField label="Number of Shares" value={shares} onChange={setShares} unit="Shares" min={1} />
        <InputField label="Buy Commission" value={buyComm} onChange={setBuyComm} unit="%" min={0} step={0.01} hint="PSX default: 0.12%" />
        <InputField label="Sell Commission" value={sellComm} onChange={setSellComm} unit="%" min={0} step={0.01} hint="PSX default: 0.12%" />
        <InputField label="Dividends per Share" value={dividends} onChange={setDividends} unit="PKR" min={0} step={0.01} hint="Optional" />
      </div>
      <CalcButton onClick={calculate} />

      {result && (
        <div className="space-y-4 animate-in fade-in duration-300">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <ResultCard label="Total Cost" value={fmt.pkr(result.cost)} />
            <ResultCard label="Total Proceeds" value={fmt.pkr(result.proceeds)} />
            <ResultCard label="Net Gain / Loss" value={fmt.pkr(result.netGain)} highlight sub={result.netGain >= 0 ? "Profit" : "Loss"} />
            <ResultCard label="ROI" value={`${result.roi.toFixed(2)}%`} highlight />
            <ResultCard label="Capital Gain" value={fmt.pkr(result.capitalGain)} />
            <ResultCard label="Dividend Income" value={fmt.pkr(result.dividendIncome)} />
          </div>
          {/* Visual bar */}
          <div className="rounded-xl bg-white/[0.02] border border-border p-4 space-y-3">
            <div className="text-[9px] font-black uppercase tracking-widest text-muted">Breakdown</div>
            <div className="space-y-2">
              {[
                { label: "Capital Gain", value: result.capitalGain, color: result.capitalGain >= 0 ? "#22c55e" : "#ef4444" },
                { label: "Dividend Income", value: result.dividendIncome, color: "#f59e0b" },
                { label: "Commission Cost", value: -(result.cost - parseFloat(buyPrice) * parseFloat(shares)) - (parseFloat(shares) * parseFloat(sellPrice) - result.proceeds + result.dividendIncome), color: "#5A6B82" },
              ].map(item => (
                <div key={item.label} className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: item.color }} />
                  <div className="text-[11px] text-soft w-32">{item.label}</div>
                  <div className="text-[11px] font-bold mono" style={{ color: item.color }}>{fmt.pkr(item.value)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <InfoBox title="PSX ROI Calculator">
        Calculates your actual return including PSX brokerage commission (0.12% standard rate). Add dividend income for a true total-return picture. Remember: PSX also charges CDC fee, NCCPL, and WHT on dividends — these are not included here.
        <div className="mt-2 font-mono text-[11px] bg-white/5 rounded-lg p-2">
          ROI = (Proceeds − Cost) / Cost × 100
        </div>
      </InfoBox>
    </div>
  );
}

// ─── 5. Zakat Calculator ─────────────────────────────────────────────────
function ZakatCalculator() {
  const [cash, setCash] = useState(0);
  const [loans, setLoans] = useState(0);
  const [investments, setInvestments] = useState(0);
  const [goldGrams, setGoldGrams] = useState(0);
  const [silverGrams, setSilverGrams] = useState(0);
  const [tradeGoods, setTradeGoods] = useState(0);
  const [borrowed, setBorrowed] = useState(0);
  const [wages, setWages] = useState(0);
  const [taxes, setTaxes] = useState(0);
  const [result, setResult] = useState(null);

  // Live gold ~PKR 26,000/g, silver ~PKR 290/g (approximate)
  const GOLD_RATE = 26000;
  const SILVER_RATE = 290;
  const NISAB_GOLD_G = 87.48;
  const NISAB_SILVER_G = 612.36;

  const calculate = useCallback(() => {
    const goldVal = (parseFloat(goldGrams) || 0) * GOLD_RATE;
    const silverVal = (parseFloat(silverGrams) || 0) * SILVER_RATE;
    const totalAssets =
      (parseFloat(cash) || 0) +
      (parseFloat(loans) || 0) +
      (parseFloat(investments) || 0) +
      goldVal + silverVal +
      (parseFloat(tradeGoods) || 0);
    const totalLiabilities =
      (parseFloat(borrowed) || 0) +
      (parseFloat(wages) || 0) +
      (parseFloat(taxes) || 0);
    const netWealth = totalAssets - totalLiabilities;
    const nisab = NISAB_SILVER_G * SILVER_RATE; // use silver nisab (lower, more common)
    const eligible = netWealth >= nisab;
    const zakatDue = eligible ? netWealth * 0.025 : 0;
    setResult({ totalAssets, totalLiabilities, netWealth, zakatDue, eligible, nisab, goldVal, silverVal });
  }, [cash, loans, investments, goldGrams, silverGrams, tradeGoods, borrowed, wages, taxes]);

  return (
    <div className="space-y-6">
      {/* Assets */}
      <div>
        <div className="text-[10px] font-black uppercase tracking-widest text-accent mb-3">Assets</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <InputField label="Cash (bank + hand)" value={cash} onChange={setCash} unit="PKR" />
          <InputField label="Loans given out (receivable)" value={loans} onChange={setLoans} unit="PKR" />
          <InputField label="Investments, shares, savings" value={investments} onChange={setInvestments} unit="PKR" hint="Include your portfolio market value" />
          <InputField label="Trade goods / inventory" value={tradeGoods} onChange={setTradeGoods} unit="PKR" />
          <InputField label="Gold weight" value={goldGrams} onChange={setGoldGrams} unit="Grams" hint={`≈ PKR ${(26000).toLocaleString()}/g`} />
          <InputField label="Silver weight" value={silverGrams} onChange={setSilverGrams} unit="Grams" hint={`≈ PKR ${(290).toLocaleString()}/g`} />
        </div>
      </div>
      {/* Liabilities */}
      <div>
        <div className="text-[10px] font-black uppercase tracking-widest text-loss mb-3">Liabilities (deducted)</div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <InputField label="Borrowed money / credit" value={borrowed} onChange={setBorrowed} unit="PKR" />
          <InputField label="Wages due to employees" value={wages} onChange={setWages} unit="PKR" />
          <InputField label="Taxes / rent due immediately" value={taxes} onChange={setTaxes} unit="PKR" />
        </div>
      </div>

      <CalcButton onClick={calculate} />

      {result && (
        <div className="space-y-4 animate-in fade-in duration-300">
          {/* Nisab eligibility banner */}
          <div className={`rounded-xl p-4 border text-sm font-semibold flex items-center gap-3 ${result.eligible ? "bg-gain/10 border-gain/30 text-gain" : "bg-white/5 border-border text-muted"}`}>
            <Star size={16} />
            {result.eligible
              ? `Zakat is obligatory — your net wealth (${fmt.pkr(result.netWealth)}) exceeds the Nisab of ${fmt.pkr(result.nisab)}`
              : `Zakat not yet due — net wealth (${fmt.pkr(result.netWealth)}) is below Nisab of ${fmt.pkr(result.nisab)}`}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <ResultCard label="Total Assets" value={fmt.pkr(result.totalAssets)} />
            <ResultCard label="Liabilities" value={fmt.pkr(result.totalLiabilities)} />
            <ResultCard label="Net Zakatable Wealth" value={fmt.pkr(result.netWealth)} />
            <ResultCard label="Zakat Due (2.5%)" value={fmt.pkr(result.zakatDue)} highlight />
          </div>
        </div>
      )}

      <InfoBox title="Nisab & Zakat Rules">
        Zakat is due at <strong className="text-white">2.5%</strong> on net wealth held for a full Islamic lunar year (hawl) if it exceeds Nisab.
        <br /><br />
        <strong className="text-white">Nisab thresholds:</strong><br />
        • Gold: 87.48g (7.5 tola) ≈ PKR {fmt.pkr(87.48 * 26000)}<br />
        • Silver: 612.36g (52.5 tola) ≈ PKR {fmt.pkr(612.36 * 290)}<br /><br />
        Scholars generally use the silver nisab as it is lower and more inclusive. Gold/silver rates used here are approximate — verify current market rates before filing.
      </InfoBox>
    </div>
  );
}

// ─── 6. Brokerage Deduction Calculator ───────────────────────────────────
function BrokerageCalculator() {
  const [price, setPrice] = useState(100);
  const [shares, setShares] = useState(1000);
  const [action, setAction] = useState("BUY");
  const [result, setResult] = useState(null);

  // PSX tiered commission schedule
  function calcCommission(pricePerShare, qty) {
    const p = parseFloat(pricePerShare) || 0;
    let ratePerShare = 0;
    if (p <= 0.05) ratePerShare = 0.005;
    else if (p <= 0.10) ratePerShare = 0.01;
    else if (p <= 0.20) ratePerShare = 0.02;
    else if (p <= 0.50) ratePerShare = 0.05;
    else ratePerShare = p * 0.0012; // 0.12%
    return ratePerShare * qty;
  }

  const calculate = useCallback(() => {
    const p = parseFloat(price) || 0;
    const q = parseFloat(shares) || 0;
    if (!p || !q) { setResult(null); return; }
    const tradeValue = p * q;
    const brokerage = calcCommission(p, q);
    // PSX additional charges (approx)
    const cdcFee = Math.max(10, tradeValue * 0.0001); // CDC charges
    const psxLevy = tradeValue * 0.00001; // PSX levy
    const secp = tradeValue * 0.000001;
    const wht = brokerage * 0.15; // 15% WHT on commission (filer)
    const totalDeductions = brokerage + cdcFee + psxLevy + secp + wht;
    const totalCost = action === "BUY" ? tradeValue + totalDeductions : tradeValue - totalDeductions;
    const effectivePrice = totalCost / q;
    setResult({ tradeValue, brokerage, cdcFee, psxLevy, secp, wht, totalDeductions, totalCost, effectivePrice });
  }, [price, shares, action]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <InputField label="Share Price" value={price} onChange={setPrice} unit="PKR" min={0.01} step={0.01} />
        <InputField label="Number of Shares" value={shares} onChange={setShares} unit="Shares" min={1} />
        <div className="space-y-1.5">
          <label className="text-[10px] font-black uppercase tracking-widest text-muted">Transaction Type</label>
          <div className="flex rounded-xl border border-border overflow-hidden">
            {["BUY", "SELL"].map(t => (
              <button
                key={t}
                onClick={() => setAction(t)}
                className={`flex-1 py-3 text-[11px] font-black uppercase tracking-widest transition-all ${action === t ? (t === "BUY" ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss") : "bg-white/[0.02] text-muted hover:text-white"}`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>
      <CalcButton onClick={calculate} />

      {result && (
        <div className="space-y-4 animate-in fade-in duration-300">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <ResultCard label="Trade Value" value={fmt.pkr(result.tradeValue)} />
            <ResultCard label="Total Deductions" value={fmt.pkr(result.totalDeductions)} />
            <ResultCard label={action === "BUY" ? "Total Cost" : "Net Proceeds"} value={fmt.pkr(result.totalCost)} highlight />
            <ResultCard label="Effective Price/Share" value={`PKR ${result.effectivePrice.toFixed(4)}`} sub="After all charges" />
          </div>
          <div className="rounded-xl bg-white/[0.02] border border-border overflow-hidden">
            <div className="px-5 py-3 border-b border-border">
              <span className="text-[10px] font-black uppercase tracking-widest text-muted">Deduction Breakdown</span>
            </div>
            <div className="divide-y divide-border">
              {[
                { label: "Brokerage Commission", value: result.brokerage, note: price <= 0.50 ? "Tiered rate" : "0.12%" },
                { label: "WHT on Commission (15%)", value: result.wht, note: "Filer rate" },
                { label: "CDC Fee", value: result.cdcFee, note: "0.01% min PKR 10" },
                { label: "PSX Levy", value: result.psxLevy, note: "0.001%" },
                { label: "SECP Fee", value: result.secp, note: "0.0001%" },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <div className="text-[12px] text-soft">{row.label}</div>
                    <div className="text-[10px] text-muted/60">{row.note}</div>
                  </div>
                  <div className="text-[12px] font-bold mono text-loss">{fmt.pkr(row.value)}</div>
                </div>
              ))}
              <div className="flex items-center justify-between px-5 py-3 bg-white/[0.02]">
                <div className="text-[12px] font-black text-white">Total Deductions</div>
                <div className="text-[13px] font-black mono text-loss">{fmt.pkr(result.totalDeductions)}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <InfoBox title="PSX Commission Structure">
        <div className="space-y-1">
          <div className="font-mono text-[11px] bg-white/5 rounded-lg p-3 space-y-0.5">
            <div>PKR 0.01–0.05 → PKR 0.005/share</div>
            <div>PKR 0.05–0.10 → PKR 0.010/share</div>
            <div>PKR 0.10–0.20 → PKR 0.020/share</div>
            <div>PKR 0.20–0.50 → PKR 0.050/share</div>
            <div>PKR 0.50+     → 0.12% of value</div>
          </div>
          <p className="mt-2">WHT on commission: 15% (filer) / 20% (non-filer). CDC, PSX levy, and SECP fees are approximate and may vary by broker.</p>
        </div>
      </InfoBox>
    </div>
  );
}

// ─── Main Tools Page ──────────────────────────────────────────────────────
const TOOLS = [
  { id: "sip",         label: "SIP",         icon: TrendingUp,  desc: "Systematic Investment Plan" },
  { id: "compounding", label: "Compounding",  icon: Repeat,      desc: "Compound Interest Growth"   },
  { id: "cagr",        label: "CAGR",         icon: BarChart2,   desc: "Annual Growth Rate"          },
  { id: "roi",         label: "ROI",          icon: DollarSign,  desc: "Return on Investment"        },
  { id: "zakat",       label: "Zakat",        icon: Star,        desc: "Islamic Wealth Obligation"   },
  { id: "brokerage",   label: "Brokerage",    icon: Calculator,  desc: "PSX Trade Deductions"        },
];

// Tools uses URL param: /tools/:toolId
export function Tools() {
  const { toolId } = useParams();

  const validTool = TOOLS.find(t => t.id === toolId);
  if (!validTool) return <Navigate to="/tools/sip" replace />;

  const tool = validTool;

  return (
    <div className="min-h-screen bg-bg">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Hero */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            PSX Financial Calculators
          </h1>
          <p className="text-muted text-sm max-w-lg mx-auto">
            Free tools to plan investments, calculate returns, estimate Zakat, and understand PSX brokerage costs.
          </p>
        </div>

        {/* Tool tabs — scrollable on mobile */}
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {TOOLS.map(t => {
            const Icon = t.icon;
            const isActive = toolId === t.id;
            return (
              <Link
                key={t.id}
                to={`/tools/${t.id}`}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest whitespace-nowrap transition-all flex-shrink-0 border ${
                  isActive
                    ? "bg-accent text-white border-accent shadow-lg shadow-accent/20"
                    : "bg-white/[0.03] text-muted border-border hover:text-white hover:bg-white/[0.06]"
                }`}
              >
                <Icon size={13} />
                {t.label}
              </Link>
            );
          })}
        </div>

        {/* Active tool card */}
        <div className="rounded-2xl bg-surface border border-border p-6 sm:p-8 shadow-2xl">
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-1">
              {tool && <tool.icon size={18} className="text-accent" />}
              <h2 className="text-lg font-black text-white">{tool?.desc}</h2>
            </div>
            <div className="h-px bg-border mt-4" />
          </div>

          {toolId === "sip"         && <SIPCalculator />}
          {toolId === "compounding" && <CompoundingCalculator />}
          {toolId === "cagr"        && <CAGRCalculator />}
          {toolId === "roi"         && <ROICalculator />}
          {toolId === "zakat"       && <ZakatCalculator />}
          {toolId === "brokerage"   && <BrokerageCalculator />}
        </div>

        {/* Cross-links */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {TOOLS.filter(t => t.id !== toolId).map(t => {
            const Icon = t.icon;
            return (
              <Link
                key={t.id}
                to={`/tools/${t.id}`}
                className="flex items-center gap-3 rounded-xl bg-white/[0.02] border border-border p-4 hover:bg-white/[0.05] hover:border-accent/30 transition-all group text-left"
              >
                <Icon size={16} className="text-muted group-hover:text-accent transition-colors flex-shrink-0" />
                <div>
                  <div className="text-[11px] font-black text-white uppercase tracking-widest">{t.label}</div>
                  <div className="text-[10px] text-muted/60">{t.desc}</div>
                </div>
                <ChevronRight size={12} className="ml-auto text-muted/30 group-hover:text-accent/50 transition-colors" />
              </Link>
            );
          })}
        </div>

        <p className="text-center text-[10px] text-muted/40">
          Calculations are for informational purposes only. Gold/silver rates are approximate. Verify with your broker and tax advisor before filing.
        </p>
      </div>
    </div>
  );
}
