const API_BASE = "http://localhost:8000";

console.log("[Sentinel BG] Service worker loaded");

chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log("[Sentinel BG] onMessage", message?.type, {
    from: sender?.url || sender?.origin || "unknown",
  });

  handleMessage(message, sender)
    .then((result) => {
      console.log("[Sentinel BG] response", message?.type, result);
      sendResponse(result);
    })
    .catch((error) => {
      console.error("[Sentinel BG] handleMessage failed", message?.type, error);
      sendResponse({ success: false, error: error?.message || "Unknown background error" });
    });

  return true;
});

async function handleMessage(message, sender) {
  const { type, payload } = message;

  switch (type) {
    case "GET_PAGE_CONTENT": {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => ({
          url: window.location.href,
          title: document.title,
          content: document.body?.innerText || "",
        }),
      });
      return results[0]?.result || {};
    }

    case "RUN_RESEARCH": {
      return await callAPI("/research", payload);
    }

    case "RUN_SYNC": {
      return await callAPI("/sync", payload);
    }

    case "RUN_CHAT": {
      console.log("[Sentinel BG] RUN_CHAT payload", payload);
      const res = await callAPI("/chat", payload);
      console.log("[Sentinel BG] RUN_CHAT response", res);
      return res;
    }

    default:
      return { error: "Unknown message type" };
  }
}

async function callAPI(endpoint, payload) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await response.json();
  } catch (error) {
    console.error(`Sentinel API error [${endpoint}]:`, error);
    return { success: false, error: error.message };
  }
}