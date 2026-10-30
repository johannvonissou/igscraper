(selector) => {
  return (document.querySelector(selector)?.innerText || "").length;
}
