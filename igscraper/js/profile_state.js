({ username, headerSelector, usernameSelector, notFoundMarkers, restrictedMarkers }) => {
  const wanted = username.toLowerCase();
  const titles = Array.from(document.querySelectorAll(usernameSelector)).filter(
    (element) => element.getClientRects().length > 0,
  );
  const title = titles.find((element) => (element.innerText || "").trim().toLowerCase() === wanted) || titles[0];

  if (title) {
    return { state: "profile", username: (title.innerText || "").trim() };
  }

  const main = document.querySelector("main");

  if (!main || document.querySelector(headerSelector)) {
    return null;
  }

  const text = (main.innerText || "").replace(/[\u2018\u2019]/g, "'").toLowerCase();

  if (notFoundMarkers.some((marker) => text.includes(marker))) {
    return { state: "not_found" };
  }

  return restrictedMarkers.some((marker) => text.includes(marker)) ? { state: "restricted" } : null;
}
