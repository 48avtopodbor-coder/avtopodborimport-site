"use client";

import { useEffect, useState } from "react";

export default function DebugPage() {
  const [info, setInfo] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    // Собираем информацию о браузере
    const lines = [
      `UA: ${navigator.userAgent}`,
      `Platform: ${navigator.platform}`,
      `Online: ${navigator.onLine}`,
      `Cookies: ${navigator.cookieEnabled}`,
      `JS: OK`,
      `Time: ${new Date().toISOString()}`,
    ];
    setInfo(lines);

    // Ловим все JS ошибки
    const handleError = (e: ErrorEvent) => {
      setErrors((prev) => [...prev, `ERROR: ${e.message} (${e.filename}:${e.lineno})`]);
    };
    const handleUnhandled = (e: PromiseRejectionEvent) => {
      setErrors((prev) => [...prev, `PROMISE: ${e.reason}`]);
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleUnhandled);

    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleUnhandled);
    };
  }, []);

  return (
    <div style={{ background: "#141414", color: "#fff", padding: 20, fontFamily: "monospace", fontSize: 12 }}>
      <h1 style={{ color: "#FF6B00", fontSize: 16, marginBottom: 16 }}>AVTOPODBOR DEBUG</h1>

      <h2 style={{ color: "#aaa", fontSize: 13, marginBottom: 8 }}>Browser Info:</h2>
      {info.map((line, i) => (
        <div key={i} style={{ marginBottom: 4, wordBreak: "break-all" }}>{line}</div>
      ))}

      <h2 style={{ color: errors.length ? "#ff4444" : "#44ff44", fontSize: 13, marginTop: 16, marginBottom: 8 }}>
        Errors: {errors.length === 0 ? "NONE ✓" : errors.length}
      </h2>
      {errors.map((err, i) => (
        <div key={i} style={{ color: "#ff4444", marginBottom: 4, wordBreak: "break-all" }}>{err}</div>
      ))}

      <div style={{ marginTop: 20, color: "#666" }}>
        <a href="/" style={{ color: "#FF6B00" }}>→ На главную</a>
      </div>
    </div>
  );
}
