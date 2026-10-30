({
  username,
  usernameSelector,
  sectionSelector,
  followerSelector,
  bioSelector,
  addressSelector,
  bioLinkSelector,
  privateText,
  postSelector,
  buttonSelector,
}) => {
  const title = document.querySelector(usernameSelector);
  const section = title?.closest("section") || document.querySelector(sectionSelector);
  const main = document.querySelector("main");
  const sectionText = section ? section.innerText || "" : "";
  const mainText = main ? main.innerText || "" : "";

  const posts = [];
  const seen = new Set();

  for (const anchor of document.querySelectorAll(postSelector)) {
    const href = anchor.getAttribute("href");

    if (!href || seen.has(href) || !href.startsWith(`/${username}/`)) {
      continue;
    }

    seen.add(href);

    const image = anchor.querySelector("img");

    posts.push({
      description: image ? image.getAttribute("alt") || "" : "",
      imageUrl: image ? image.getAttribute("src") : null,
    });
  }

  return {
    sectionText,
    followersTitle: document.querySelector(followerSelector)?.getAttribute("title") ?? null,
    bio: document.querySelector(bioSelector)?.innerText?.trim() || "",
    address: document.querySelector(addressSelector)?.innerText?.trim() || null,
    bioLink: document.querySelector(bioLinkSelector)?.getAttribute("href") || null,
    appearsPrivate: sectionText.includes(privateText) || mainText.includes(privateText),
    buttonTexts: Array.from(document.querySelectorAll(buttonSelector)).map((element) =>
      (element.innerText || "").trim(),
    ),
    posts,
  };
}
