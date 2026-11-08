/** API base URL — set window.__FACULTYLINK_API_BASE__ before app scripts, or use default local Flask. */
export function getApiBase() {
  const fromWindow = typeof window !== 'undefined' && window.__FACULTYLINK_API_BASE__;
  if (fromWindow && String(fromWindow).trim()) {
    return String(fromWindow).replace(/\/$/, '');
  }
  // Match the page host so the session cookie is same-site (localhost ≠ 127.0.0.1).
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return `http://${window.location.hostname}:5000`;
  }
  return 'http://127.0.0.1:5000';
}
