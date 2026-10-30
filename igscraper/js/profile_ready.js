({ selector, markers }) => {
  const element = document.querySelector(selector);

  if (!element) {
    return false;
  }

  const text = element.innerText || "";

  if (!text.trim()) {
    return false;
  }

  return markers.some((marker) => text.includes(marker));
}
