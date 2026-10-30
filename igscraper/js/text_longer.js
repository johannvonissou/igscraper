({ selector, length }) => {
  return (document.querySelector(selector)?.innerText || "").length > length;
}
