chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "EXTRACT_CONTENT") {
    sendResponse({
      url: window.location.href,
      title: document.title,
      content: document.body?.innerText || "",
      metaDescription: document.querySelector('meta[name="description"]')?.content || "",
    });
  }
  return true;
});