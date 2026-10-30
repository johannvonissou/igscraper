(selector) => {
  return Array.from(document.querySelectorAll(selector)).map((element) => (element.innerText || "").trim());
}
