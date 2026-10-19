// Apply the saved appearance before styles and Python load, avoiding a light flash.
(() => {
  const storageKey = 'tyaga-theme';
  const root = document.documentElement;
  let current = 'light';

  function apply(value) {
    current = value === 'dark' ? 'dark' : 'light';
    root.dataset.theme = current;
    root.style.colorScheme = current;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', current === 'dark' ? '#1c2b30' : '#ffffff');
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.setAttribute('aria-checked', String(current === 'dark'));
      button.title = current === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему';
    });
  }

  function set(value) {
    apply(value);
    try { localStorage.setItem(storageKey, current); } catch { /* Still usable for this visit. */ }
  }

  try { current = localStorage.getItem(storageKey) === 'dark' ? 'dark' : 'light'; } catch { /* Keep light as the default. */ }
  apply(current);
  window.TyagaTheme = Object.freeze({get: () => current, set, toggle: () => set(current === 'dark' ? 'light' : 'dark')});

  document.addEventListener('click', event => {
    if (!event.target.closest?.('[data-theme-toggle]')) return;
    event.preventDefault();
    window.TyagaTheme.toggle();
  });
  window.addEventListener('storage', event => {
    if (event.key === storageKey || event.key === null) apply(event.newValue);
  });
})();
