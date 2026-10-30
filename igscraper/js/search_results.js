({ scopeSelector, tabSelector, prefix, imgSelector, linkSelector, separator, followerSuffixes }) => {
  const scope = document.querySelector(scopeSelector);
  const tablist = scope?.querySelector(tabSelector)?.closest('[role="tablist"]');

  if (!tablist) {
    return null;
  }

  const after = (node) => Boolean(tablist.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING);
  const links = Array.from(scope.querySelectorAll(linkSelector)).filter(after);
  const accounts = [];
  const seen = new Set();

  for (const img of Array.from(scope.querySelectorAll(imgSelector)).filter(after)) {
    const alt = img.getAttribute("alt") || "";

    if (!alt.startsWith(prefix)) {
      continue;
    }

    const username = alt.slice(prefix.length).trim();
    const link = img.closest(linkSelector);

    if (!username || !link || seen.has(username)) {
      continue;
    }

    const href = link.getAttribute("href") || "";

    if (href.replace(/^\/+|\/+$/g, "").split("/")[0] !== username) {
      continue;
    }

    const lines = [];

    for (const candidate of links) {
      if (candidate.getAttribute("href") !== href) {
        continue;
      }

      for (const line of (candidate.innerText || "").split("\n")) {
        const text = line.trim();

        if (text && text !== username && !lines.includes(text)) {
          lines.push(text);
        }
      }
    }

    const parts = (lines[0] || "")
      .split(separator)
      .map((part) => part.trim())
      .filter(Boolean);
    const isFollowers = (part) => followerSuffixes.some((suffix) => part.toLowerCase().endsWith(suffix));
    const followers = parts.find(isFollowers) || null;
    const name = parts.filter((part) => !isFollowers(part)).join(` ${separator} `) || username;

    accounts.push({
      profilePictureUrl: img.getAttribute("src"),
      username,
      name,
      followers,
      url: new URL(href, location.href).href,
    });

    seen.add(username);
  }

  return accounts;
}
