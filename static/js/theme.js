(function () {
  var STORAGE_KEY = 'lexitrace-theme';
  var root = document.documentElement;
  var media = window.matchMedia('(prefers-color-scheme: dark)');

  function storedTheme() {
    try {
      var value = localStorage.getItem(STORAGE_KEY);
      return value === 'light' || value === 'dark' ? value : null;
    } catch (error) {
      return null;
    }
  }

  function preferredTheme() {
    return storedTheme() || (media.matches ? 'dark' : 'light');
  }

  function applyTheme(theme) {
    root.setAttribute('data-bs-theme', theme);
    var button = document.getElementById('theme-toggle');
    if (!button) {
      return;
    }
    var next = theme === 'dark' ? 'light' : 'dark';
    var label = 'Switch to ' + next + ' mode';
    var icon = button.querySelector('i');
    if (icon) {
      icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
    }
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
  }

  function toggleTheme() {
    var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (error) {
    }
    applyTheme(next);
  }

  applyTheme(preferredTheme());

  var toggle = document.getElementById('theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', toggleTheme);
  }

  media.addEventListener('change', function () {
    if (!storedTheme()) {
      applyTheme(preferredTheme());
    }
  });
})();
