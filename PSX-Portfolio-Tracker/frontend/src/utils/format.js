export const fmt = {
  pkr: (n, decimals = 2) => {
    if (n == null) return "—";
    return `PKR ${Number(n).toLocaleString("en-PK", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}`;
  },

  num: (n, decimals = 2) => {
    if (n == null) return "—";
    return Number(n).toLocaleString("en-PK", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  },

  pct: (n) => {
    if (n == null) return "—";
    const sign = n >= 0 ? "+" : "";
    return `${sign}${Number(n).toFixed(2)}%`;
  },

  date: (str) => {
    if (!str) return "—";
    return new Date(str).toLocaleDateString("en-PK", {
      day: "2-digit", month: "short", year: "numeric",
    });
  },

  compact: (n) => {
    if (n == null) return "—";
    if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
    if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(Number(n).toFixed(2));
  },
};

export function gainClass(n) {
  if (n == null) return "text-gray-400";
  return n >= 0 ? "text-green-400" : "text-red-400";
}
