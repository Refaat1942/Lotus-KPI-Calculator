function syncDmyFields(form) {
  form.querySelectorAll('.dmy-picker').forEach(picker => {
    const prefix = picker.dataset.prefix;
    const day = picker.querySelector('.dmy-day')?.value;
    const month = picker.querySelector('.dmy-month')?.value;
    const year = picker.querySelector('.dmy-year')?.value;
    const hidden = picker.querySelector('.dmy-hidden');
    if (hidden && day && month && year) {
      hidden.value = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });

  document.querySelectorAll('table tbody tr').forEach((row, i) => {
    row.style.animationDelay = `${i * 0.03}s`;
  });

  document.querySelectorAll('.dmy-form').forEach(form => {
    form.addEventListener('submit', () => syncDmyFields(form));
  });
});
