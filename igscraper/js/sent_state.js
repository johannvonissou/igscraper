({ articleSelector, composerSelector, message }) => {
  const echoed = Array.from(document.querySelectorAll(articleSelector)).some((article) =>
    (article.innerText || "").includes(message),
  );

  if (!echoed) {
    return false;
  }

  const composer = document.querySelector(composerSelector);

  return !((composer?.innerText) || "").trim();
}
