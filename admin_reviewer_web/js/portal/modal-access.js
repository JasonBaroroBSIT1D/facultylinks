/** Body-level modal helpers (escape stacking / overflow clipping). */

export function modalHost() {
  return document.getElementById('modalRoot');
}

export function lockPageScroll(on) {
  document.body.classList.toggle('fl-modal-open', on);
}

export function teardownModal(host, restoreFocusEl) {
  if (host?._flTrapKeydown) {
    document.removeEventListener('keydown', host._flTrapKeydown);
    delete host._flTrapKeydown;
  }
  if (host) host.innerHTML = '';
  lockPageScroll(false);
  if (restoreFocusEl && typeof restoreFocusEl.focus === 'function') restoreFocusEl.focus();
}

export function bindModalShell({ host, overlay, dialog, onRequestClose, restoreFocusEl }) {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) onRequestClose();
  });

  const onKey = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onRequestClose();
      return;
    }
    if (e.key !== 'Tab' || !dialog) return;
    const nodes = dialog.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (!nodes.length) return;
    const list = [...nodes];
    const first = list[0];
    const last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  host._flTrapKeydown = onKey;
  document.addEventListener('keydown', onKey);

  lockPageScroll(true);
  const firstFocus =
    dialog.querySelector('[data-autofocus]') ||
    dialog.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
  firstFocus?.focus();

  return () => teardownModal(host, restoreFocusEl);
}

/** Attach body-level centered modal; returns { host, dialog, close }. */
const SIZE_CLASS = {
  md: 'fl-modal-dialog--md',
  lg: 'fl-modal-dialog--lg',
  account: 'fl-modal-dialog--account',
};

export function openCenteredModal({
  title,
  lede,
  size = 'md',
  iconHtml = '',
  bodyHtml,
  footerHtml,
  opener,
  onBeforeClose,
}) {
  const host = modalHost();
  if (!host) return null;
  const sizeClass = SIZE_CLASS[size] || SIZE_CLASS.md;
  const dialogId = `fl-modal-${Date.now()}`;
  const hasBody = bodyHtml != null && String(bodyHtml).trim() !== '';
  host.innerHTML = `
    <div class="fl-modal-overlay" id="${dialogId}-overlay" role="presentation">
      <div class="fl-modal-dialog ${sizeClass}${hasBody ? '' : ' fl-modal-dialog--no-body'}" role="dialog" aria-modal="true" aria-labelledby="${dialogId}-title" id="${dialogId}-dialog">
        <header class="fl-modal-dialog__header${iconHtml ? ' fl-modal-dialog__header--icon' : ''}">
          ${iconHtml ? `<span class="fl-modal-dialog__icon" aria-hidden="true">${iconHtml}</span>` : ''}
          <div class="fl-modal-dialog__titles">
            <h2 id="${dialogId}-title">${title ?? ''}</h2>
            ${lede ? `<p class="fl-modal-dialog__lede">${lede}</p>` : ''}
          </div>
          <button type="button" class="fl-modal-close" data-fl-modal-dismiss aria-label="Close dialog">×</button>
        </header>
        ${hasBody ? `<div class="fl-modal-dialog__body">${bodyHtml}</div>` : ''}
        ${footerHtml ? `<footer class="fl-modal-dialog__footer">${footerHtml}</footer>` : ''}
      </div>
    </div>
  `;
  const overlay = host.querySelector(`#${dialogId}-overlay`);
  const dialog = host.querySelector(`#${dialogId}-dialog`);
  const close = () => {
    if (onBeforeClose && onBeforeClose() === false) return;
    teardownModal(host, opener);
  };
  bindModalShell({ host, overlay, dialog, onRequestClose: close, restoreFocusEl: opener });
  dialog.querySelector('[data-fl-modal-dismiss]')?.addEventListener('click', close);
  dialog.querySelectorAll('[data-fl-modal-cancel]').forEach((b) => b.addEventListener('click', close));
  return { host, dialog, close };
}

/** Right-side drawer on #modalRoot (edit panels). */
export function openDrawerModal({ panelHtml, opener }) {
  const host = modalHost();
  if (!host) return null;
  const id = `fl-drawer-${Date.now()}`;
  host.innerHTML = `
    <div class="fl-modal-overlay fl-modal-overlay--drawer" id="${id}-overlay" role="presentation">
      ${panelHtml}
    </div>
  `;
  const overlay = host.querySelector(`#${id}-overlay`);
  const dialog = overlay.querySelector('.cfg-side-panel');
  const close = () => teardownModal(host, opener);
  bindModalShell({
    host,
    overlay,
    dialog: dialog || overlay,
    onRequestClose: close,
    restoreFocusEl: opener,
  });
  return { host, dialog, close };
}
