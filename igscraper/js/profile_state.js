({ headerSelector, usernameSelector, notFoundMarkers }) => {
  const username = document.querySelector(usernameSelector);

  if (username && username.getClientRects().length > 0) {
    return "profile";
  }

  const main = document.querySelector("main");

  if (!main || document.querySelector(headerSelector)) {
    return null;
  }

  const text = (main.innerText || "").replace(/[‘’]/g, "'").toLowerCase();

  return notFoundMarkers.some((marker) => text.includes(marker)) ? "not_found" : null;
}
