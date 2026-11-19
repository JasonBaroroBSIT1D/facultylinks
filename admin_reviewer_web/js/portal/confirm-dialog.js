import { openCenteredModal, teardownModal } from './modal-access.js';

/**
 * FacultyLink-styled confirm dialog. Resolves true if primary/confirmed, false if cancelled.
 */
export function openConfirmDialog({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  opener,
}) {
  return new Promise((resolve) => {
    const modal = openCenteredModal({
      title,
      lede: message,
      size: 'md',
      bodyHtml: '',
      footerHtml: `
        <button type="button" class="cfg-btn-primary" data-confirm-cancel>${cancelLabel}</button>
        <button type="button" class="${destructive ? 'cfg-btn-secondary' : 'cfg-btn-primary'}" data-confirm-ok>${confirmLabel}</button>`,
      opener,
      onBeforeClose: () => false,
    });
    if (!modal) {
      resolve(false);
      return;
    }

    const finish = (value) => {
      teardownModal(modal.host, opener);
      resolve(value);
    };

    modal.dialog.querySelector('[data-confirm-cancel]')?.addEventListener('click', () => finish(false));
    modal.dialog.querySelector('[data-confirm-ok]')?.addEventListener('click', () => finish(true));
    modal.dialog.querySelector('.fl-modal-close')?.addEventListener('click', () => finish(false));

    const cancelBtn = modal.dialog.querySelector('[data-confirm-cancel]');
    cancelBtn?.focus();
  });
}

/** Discard unsaved account form changes (Add/Edit Reviewer or Faculty). */
export function confirmDiscardUnsavedChanges({ opener } = {}) {
  return openConfirmDialog({
    title: 'Discard unsaved changes?',
    message: 'Your changes haven’t been saved. If you leave, they will be lost.',
    cancelLabel: 'Keep editing',
    confirmLabel: 'Discard changes',
    destructive: true,
    opener,
  }).then((ok) => ok);
}