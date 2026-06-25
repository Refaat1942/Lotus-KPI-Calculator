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
});
