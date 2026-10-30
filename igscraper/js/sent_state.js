({ articleSelector, composerSelector, message, before }) => {
  const normalize = (text) => (text || "").replace(/\s+/g, " ").trim();
  const wanted = normalize(message);
  const echoed = Array.from(document.querySelectorAll(articleSelector)).filter((article) =>
    normalize(article.innerText).includes(wanted),
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
