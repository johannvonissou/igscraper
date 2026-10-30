({ prefix, imgSelector, namesSelector, linkSelector }) => {
  const accounts = [];
  const seen = new Set();

  for (const img of document.querySelectorAll(imgSelector)) {
    const alt = img.getAttribute("alt") || "";

    if (!alt.startsWith(prefix)) {
      continue;
    }

    const username = alt.slice(prefix.length).trim();

    if (!username || seen.has(username)) {
      continue;
    }

    let container = img.closest("div");

    while (container && !container.querySelector(namesSelector)) {
      container = container.parentElement;
    }

    if (!container) {
      continue;
    }

    const labels = [];

    for (const span of container.querySelectorAll(namesSelector)) {
      const text = (span.textContent || "").trim();

      if (text && !labels.includes(text)) {
        labels.push(text);
      }
    }

    const name = labels.find((label) => label !== username) || username;
    let url = null;

    for (const link of container.querySelectorAll(linkSelector)) {
      const href = link.getAttribute("href");

      if (!href) {
        continue;
      }

      const firstSegment = href.replace(/^\/+|\/+$/g, "").split("/")[0];

      if (firstSegment !== username) {
        continue;
      }

      url = new URL(href, location.href).href;
      break;
    }

    if (url === null) {
      continue;
    }

    accounts.push({
      profilePictureUrl: img.getAttribute("src"),
      username,
      name,
      url,
    });

    seen.add(username);
  }

  return accounts;
}
