// Проверка форм в браузере, маска телефона, подтверждение удаления.
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
    rating: v => v !== '' || 'Поставьте оценку от 1 до 5',
    body: v => v.trim().length >= 10 || 'Отзыв — от 10 до 1000 символов',
  };

  const valueOf = (form, el) => el.type === 'radio'
    ? (form.querySelector(`input[name="${el.name}"]:checked`) || { value: '' }).value
    : el.value;

  const check = (form, el) => {
    const rule = rules[el.name];
    if (!rule) return true;
    const res = rule(valueOf(form, el));
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
    fields.forEach(el => {
      el.addEventListener(el.type === 'radio' ? 'change' : 'blur', () => check(form, el));
      // как только пользователь исправил значение — убираем ошибку сразу, не дожидаясь ухода с поля
      el.addEventListener('input', () => { if (el.closest('.field--error')) check(form, el); });
    });
    form.addEventListener('submit', e => {
      const seen = new Set();
      const bad = fields.filter(el => {
        if (seen.has(el.name)) return false;
        seen.add(el.name);
        return !check(form, el);
      });
      if (bad.length) { e.preventDefault(); bad[0].focus(); }
    });
  });

  document.querySelectorAll('form[data-confirm]').forEach(f =>
    f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));
})();
