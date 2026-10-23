// Переключатель языка RU/EN. Подключается синхронно в <head>, чтобы язык
// выставился до первой отрисовки. Тексты обоих языков лежат в разметке
// рядом (<span lang="ru">…</span><span lang="en">…</span>), CSS прячет
// неактивный. Выбор хранится в localStorage под тем же ключом, что слушает
// эмулятор в iframe — он переключается вместе со страницей.
(function () {
  'use strict';
  var KEY = 'dash-bmw-lang';

  // Ссылка на страницу приёма донатов. Пустая строка — кнопка не показывается.
  var SUPPORT_URL = '';

  function initial() {
    var q = /[?&]lang=(ru|en)/.exec(location.search);
    if (q) return q[1];
    try {
      var s = localStorage.getItem(KEY);
      if (s === 'ru' || s === 'en') return s;
    } catch (e) {}
    return (navigator.language || '').toLowerCase().indexOf('ru') === 0 ? 'ru' : 'en';
  }

  var root = document.documentElement;

  function apply(lang) {
    root.setAttribute('data-lang', lang);
    root.lang = lang;
    var title = root.getAttribute('data-title-' + lang);
    if (title) document.title = title;
    var btn = document.querySelector('.lang-toggle');
    if (btn) {
      btn.textContent = lang === 'ru' ? 'EN' : 'RU';
      btn.setAttribute('aria-label', lang === 'ru' ? 'Switch to English' : 'Переключить на русский');
    }
    document.dispatchEvent(new CustomEvent('langchange', { detail: lang }));
  }

  apply(initial());

  document.addEventListener('DOMContentLoaded', function () {
    apply(root.getAttribute('data-lang'));
    var btn = document.querySelector('.lang-toggle');
    if (btn) {
      btn.addEventListener('click', function () {
        var next = root.getAttribute('data-lang') === 'ru' ? 'en' : 'ru';
        try { localStorage.setItem(KEY, next); } catch (e) {}
        apply(next);
      });
    }
    var support = document.querySelectorAll('[data-support]');
    for (var i = 0; i < support.length; i++) {
      if (SUPPORT_URL) support[i].setAttribute('href', SUPPORT_URL);
      else support[i].hidden = true;
    }
  });
})();
