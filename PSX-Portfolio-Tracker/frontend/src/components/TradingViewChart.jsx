import React, { useEffect, useRef } from 'react';

export function TradingViewChart({ symbol }) {
  const container = useRef();

  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      "autosize": true,
      "symbol": `PSX:${symbol.toUpperCase()}`,
      "interval": "D",
      "timezone": "Asia/Karachi",
      "theme": "dark",
      "style": "1",
      "locale": "en",
      "allow_symbol_change": false,
      "calendar": false,
      "support_host": "https://www.tradingview.com"
    });
    
    // Clear existing children
    if (container.current) {
        container.current.innerHTML = '';
        container.current.appendChild(script);
    }
  }, [symbol]);

  return (
    <div className="tradingview-widget-container h-full w-full rounded-2xl overflow-hidden" ref={container}>
      <div className="tradingview-widget-container__widget h-full w-full"></div>
    </div>
  );
}
