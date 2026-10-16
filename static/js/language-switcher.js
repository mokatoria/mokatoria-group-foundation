/* Navigate directly so a translation proxy cannot rewrite the language choices. */
(function () {
  'use strict';
  const picker = document.querySelector('.translation-menu');
  if (!picker) return;
  const original = new URL(picker.dataset.publicUrl);
  if (original.origin !== 'https://mokatoriagroupfoundation.com') return;
  const currentLanguage = location.hostname.endsWith('.translate.goog')
    ? new URLSearchParams(location.search).get('_x_tr_tl') : 'en';
  picker.querySelectorAll('button[data-language]').forEach(function (button) {
    if (button.dataset.language === currentLanguage) button.setAttribute('aria-current', 'true');
  });
  picker.addEventListener('click', function (event) {
    const button = event.target.closest('button[data-language]');
    if (!button || !picker.contains(button)) return;
    event.preventDefault();
    event.stopPropagation();
    original.hash = location.hash;
    picker.open = false;
    const language = button.dataset.language;
    if (language === 'en') {
      window.location.assign(original.href);
      return;
    }
    const destination = new URL(language === 'more'
      ? 'https://translate.google.com/' : 'https://translate.google.com/translate');
    destination.searchParams.set('sl', 'en');
    destination.searchParams.set('tl', language === 'more' ? 'sw' : language);
    if (language === 'more') {
      destination.searchParams.set('op', 'websites');
      destination.searchParams.set('text', original.href);
    } else {
      destination.searchParams.set('u', original.href);
    }
    window.location.assign(destination.href);
  });
})();
