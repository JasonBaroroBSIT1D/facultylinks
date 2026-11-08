/** Reusable compact brand HTML (original logo image). */

export function brandCompactHtml({ onDark = false, auth = false, base = 'assets/' } = {}) {
  const mods = [
    'fl-brand-compact',
    onDark ? 'fl-brand-compact--on-dark' : '',
    auth ? 'fl-brand-compact--auth' : '',
  ]
    .filter(Boolean)
    .join(' ');

  if (auth) {
    return `
    <div class="${mods}">
      <img class="fl-brand-logo-img" src="${base}FacultyLink-logo.jpg" alt="FacultyLink" />
    </div>`;
  }

  return `
    <div class="${mods}">
      <img class="fl-brand-logo-img" src="${base}FacultyLink-logo.jpg" alt="" aria-hidden="true" />
      <span class="fl-brand-wordmark">
        <span class="wm-title"><span class="wm-faculty">Faculty</span><span class="wm-link">Link</span></span>
      </span>
    </div>`;
}
