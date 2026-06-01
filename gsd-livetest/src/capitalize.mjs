export function capitalize(text) {
  const s = String(text);
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}
