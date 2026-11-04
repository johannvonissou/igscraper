({ articleSelector, composerSelector, message, before }) => {
  const normalize = (text) => (text || "").replace(/\s+/g, " ").trim();
  const readable = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let text = "";

    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === Node.TEXT_NODE) {
        text += node.nodeValue;
      } else if (node.tagName === "IMG") {
        text += node.alt || "";
      } else if (node.tagName === "BR") {
        text += " ";
      }
    }

    return normalize(text);
  };
  const wanted = normalize(message);
  const echoed = Array.from(document.querySelectorAll(articleSelector)).filter((article) =>
    readable(article).includes(wanted),
  ).length;

  if (before === undefined) {
    return echoed;
  }

  if (echoed <= before) {
    return false;
  }

  const composer = document.querySelector(composerSelector);

  return !normalize(composer?.innerText);
}
