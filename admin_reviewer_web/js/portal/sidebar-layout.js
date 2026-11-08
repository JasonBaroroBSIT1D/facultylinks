const STORAGE_KEY = 'facultylink_sidebar_collapsed_v1';
const MOBILE_QUERY = '(max-width: 900px)';

const layout = {
  mobileOpen: false,
  desktopCollapsed: false,
};

let mobileMq = null;
let initialized = false;

export function isMobileViewport() {
  return mobileMq?.matches ?? window.matchMedia(MOBILE_QUERY).matches;
}

export function initSidebarLayout() {
  if (initialized) return;
  initialized = true;
  mobileMq = window.matchMedia(MOBILE_QUERY);
  try {
    layout.desktopCollapsed = localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    layout.desktopCollapsed = false;
  }

  const toggle = document.getElementById('toggleSidebar');
  const backdrop = document.getElementById('sidebarBackdrop');

  toggle?.addEventListener('click', () => toggleSidebar());
  backdrop?.addEventListener('click', () => closeMobileDrawer(true));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && layout.mobileOpen) {
      e.preventDefault();
      closeMobileDrawer(true);
    }
  });

  mobileMq.addEventListener('change', () => {
    layout.mobileOpen = false;
    applySidebarLayout();
  });

  applySidebarLayout();
}

export function applySidebarLayout() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const toggle = document.getElementById('toggleSidebar');
  if (!sidebar || !toggle) return;

  const mobile = isMobileViewport();

  if (mobile) {
    sidebar.classList.remove('collapsed');
    sidebar.classList.toggle('open', layout.mobileOpen);
    backdrop?.classList.toggle('is-visible', layout.mobileOpen);
    backdrop?.setAttribute('aria-hidden', layout.mobileOpen ? 'false' : 'true');
    document.body.classList.toggle('sidebar-drawer-open', layout.mobileOpen);
    toggle.setAttribute('aria-expanded', String(layout.mobileOpen));
    toggle.setAttribute(
      'aria-label',
      layout.mobileOpen ? 'Close navigation menu' : 'Open navigation menu'
    );
  } else {
    sidebar.classList.remove('open');
    sidebar.classList.toggle('collapsed', layout.desktopCollapsed);
    backdrop?.classList.remove('is-visible');
    backdrop?.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('sidebar-drawer-open');
    const expanded = !layout.desktopCollapsed;
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.setAttribute('aria-label', layout.desktopCollapsed ? 'Expand sidebar navigation' : 'Collapse sidebar navigation');
  }

  toggle.setAttribute('aria-controls', 'sidebar');
}

export function toggleSidebar() {
  if (isMobileViewport()) {
    layout.mobileOpen = !layout.mobileOpen;
  } else {
    layout.desktopCollapsed = !layout.desktopCollapsed;
    try {
      localStorage.setItem(STORAGE_KEY, layout.desktopCollapsed ? '1' : '0');
    } catch {
      /* ignore */
    }
  }
  applySidebarLayout();
}

/** Close mobile drawer without clearing desktop collapsed state. */
export function closeMobileDrawer(returnFocus = true) {
  if (!layout.mobileOpen) return;
  layout.mobileOpen = false;
  applySidebarLayout();
  if (returnFocus) document.getElementById('toggleSidebar')?.focus();
}
