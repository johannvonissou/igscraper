({
  username,
  usernameSelector,
  sectionSelector,
  followerSelector,
  bioSelector,
  addressSelector,
  bioLinkSelector,
  bioLinkExcludedHosts,
  bioLinkButtonSelector,
  bioLinkButtonPattern,
  bioLinkScheme,
  privateText,
  postSelector,
  postHrefPattern,
  buttonSelector,
}) => {
  const titles = Array.from(document.querySelectorAll(usernameSelector));
  const title =
    titles.find((element) => (element.innerText || "").trim().toLowerCase() === username.toLowerCase()) || titles[0];
  const section = title?.closest("section") || document.querySelector(sectionSelector);
  const main = document.querySelector("main");
  const sectionText = section ? section.innerText || "" : "";
  const mainText = main ? main.innerText || "" : "";

  const postPattern = new RegExp(postHrefPattern);
  const posts = [];
  const seen = new Set();

  for (const anchor of document.querySelectorAll(postSelector)) {
    const href = anchor.getAttribute("href");

    if (!href || seen.has(href) || !postPattern.test(href)) {
      continue;
    }

    seen.add(href);

    const image = anchor.querySelector("img");

    posts.push({
      description: image ? image.getAttribute("alt") || "" : "",
      imageUrl: image ? image.getAttribute("src") : null,
      url: new URL(href, location.href).href,
    });
  }

  const isExcluded = (href) => {
    try {
      const host = new URL(href).hostname;

      return bioLinkExcludedHosts.some((excluded) => host === excluded || host.endsWith(`.${excluded}`));
    } catch {
      return true;
    }
  };
  const anchor = Array.from(document.querySelectorAll(bioLinkSelector)).find(
    (element) => !isExcluded(element.href),
  );
  const pattern = new RegExp(bioLinkButtonPattern, "i");
  const button = Array.from(document.querySelectorAll(bioLinkButtonSelector))
    .map((element) => (element.innerText || "").trim().match(pattern))
    .find(Boolean);
  const bioLink = anchor ? anchor.getAttribute("href") : button ? `${bioLinkScheme}${button[1]}` : null;

  return {
    sectionText,
    followersTitle: document.querySelector(followerSelector)?.getAttribute("title") ?? null,
    bio: document.querySelector(bioSelector)?.innerText?.trim() || "",
    address:
      Array.from(document.querySelectorAll(addressSelector))
        .find((element) => element !== title)
        ?.innerText?.trim() || null,
    bioLink,
    appearsPrivate: sectionText.includes(privateText) || mainText.includes(privateText),
    buttonTexts: Array.from(document.querySelectorAll(buttonSelector)).map((element) =>
      (element.innerText || "").trim(),
    ),
    posts,
  };
}
