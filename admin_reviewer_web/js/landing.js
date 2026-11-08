document.getElementById('yr').textContent = new Date().getFullYear();

const headerH = () => parseInt(getComputedStyle(document.documentElement).getPropertyValue('--fl-header-h')) || 90;

document.querySelectorAll('a[href^="#"]').forEach((a) => {
  a.addEventListener('click', (e) => {
    const id = a.getAttribute('href');
    if (!id || id === '#') return;
    const el = document.querySelector(id);
    if (!el) return;
    e.preventDefault();
    const y = el.getBoundingClientRect().top + window.scrollY - headerH() + 4;
    window.scrollTo({ top: y, behavior: 'smooth' });
  });
});

const links = [...document.querySelectorAll('.nav-link')];
const sections = links.map((l) => document.querySelector(l.getAttribute('href'))).filter(Boolean);

const obs = new IntersectionObserver(
  (entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) {
        const id = en.target.id;
        links.forEach((l) => l.classList.toggle('active', l.dataset.section === id));
      }
    });
  },
  { rootMargin: `-${headerH()}px 0px -55% 0px`, threshold: 0.1 }
);
sections.forEach((s) => obs.observe(s));
