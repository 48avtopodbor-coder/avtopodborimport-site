import { useState } from "react";

export default function BrowserInfo() {
  const [lines] = useState(() => [
    `UA: ${navigator.userAgent}`,
    `Platform: ${navigator.platform}`,
    `Online: ${navigator.onLine}`,
    `Cookies: ${navigator.cookieEnabled}`,
    "JS: OK",
    `Time: ${new Date().toISOString()}`,
  ]);

  return lines.map((line) => (
    <div key={line} style={{ marginBottom: 4, wordBreak: "break-all" }}>
      {line}
    </div>
  ));
}
