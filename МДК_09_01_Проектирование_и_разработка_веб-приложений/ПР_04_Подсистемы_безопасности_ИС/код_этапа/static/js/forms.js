// Проверка форм в браузере и маска телефона (ПР 4: валидация на клиенте).
// Сервер проверяет всё повторно — эти правила только ускоряют обратную связь.
(() => {
  const rules = {
    login: v => /^[A-Za-z0-9._-]{3,24}$/.test(v.trim()) || 'Логин: 3–24 символа — латинские буквы, цифры, точка, дефис, подчёркивание',
    full_name: v => /^[А-ЯЁа-яё]+(?:[ -][А-ЯЁа-яё]+)+$/.test(v.trim().replace(/\s+/g, ' ')) || 'Укажите фамилию и имя русскими буквами',
    email: v => /^[^@\s]+@[^@\s]+\.[A-Za-zА-Яа-я]{2,}$/.test(v.trim()) || 'Почта в формате name@example.ru',
    phone: v => /^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$/.test(v.trim()) || 'Телефон в формате +7 (999) 123-45-67',
    password: v => (v.length >= 8 && /[A-Za-zА-Яа-яЁё]/.test(v) && /\d/.test(v) && v === v.trim()) || 'Пароль — от 8 символов, буквы и цифры, без пробелов по краям',
    password2: v => v === (document.getElementById('password') || {}).value || 'Пароли не совпадают',
    action_id: v => v !== '' || 'Выберите акцию',
    task: v => v !== '' || 'Выберите, чем хотите помочь',
  };

  const check = el => {
    const rule = rules[el.name];
    if (!rule) return true;
    const res = rule(el.value);
    const box = el.closest('.field');
    box.classList.toggle('field--error', res !== true);
    box.querySelector('.field__err').textContent = res === true ? '' : res;
    return res === true;
  };

  // маска: из любых цифр собираем +7 (XXX) XXX-XX-XX
  const phone = document.getElementById('phone');
  if (phone) phone.addEventListener('input', () => {
    let d = phone.value.replace(/\D/g, '');
    if (d.startsWith('8') || d.startsWith('7')) d = d.slice(1);
    d = d.slice(0, 10);
    const p = [d.slice(0, 3), d.slice(3, 6), d.slice(6, 8), d.slice(8, 10)];
    phone.value = d ? '+7 (' + p[0] + (d.length > 3 ? ') ' + p[1] : '') + (d.length > 6 ? '-' + p[2] : '') + (d.length > 8 ? '-' + p[3] : '') : '';
  });

  document.querySelectorAll('form[data-validate]').forEach(form => {
    const fields = [...form.querySelectorAll('input:not([type=hidden]), select, textarea')];
    fields.forEach(el => el.addEventListener('blur', () => check(el)));
    form.addEventListener('submit', e => {
      const bad = fields.filter(el => !check(el));
      if (bad.length) { e.preventDefault(); bad[0].focus(); }
    });
  });
})();
