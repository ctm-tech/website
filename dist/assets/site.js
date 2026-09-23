// Mobile nav
const menuToggle = document.getElementById('menuToggle');
const navLinks = document.getElementById('navLinks');
menuToggle.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  menuToggle.setAttribute('aria-expanded', String(open));
});
navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  navLinks.classList.remove('open');
  menuToggle.setAttribute('aria-expanded', 'false');
}));

// Reveal on scroll
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
} else {
  document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
}

// Contact form → /api/contact (Cloudflare Pages Function)
const form = document.getElementById('contact-form');
if (form) {
  const confirmMsg = document.getElementById('confirmMsg');
  const submitBtn = form.querySelector('button[type=submit]');

  // Links like /contact/?type=Home%20Assistant preselect the enquiry type
  const wanted = new URLSearchParams(location.search).get('type');
  const typeSelect = document.getElementById('f-type');
  if (wanted && [...typeSelect.options].some(o => o.value === wanted)) typeSelect.value = wanted;

  function say(text, isError) {
    confirmMsg.textContent = text;
    confirmMsg.classList.toggle('error', !!isError);
    confirmMsg.classList.add('show');
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!form.checkValidity()) { form.reportValidity(); return; }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending…';
    confirmMsg.classList.remove('show');

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      });
      const out = await res.json().catch(() => ({ ok: false, message: 'Unexpected response from the server.' }));
      say(out.message, !out.ok);
      if (out.ok) {
        form.reset();
        if (window.turnstile) window.turnstile.reset();
      }
    } catch {
      say('Could not reach the server. Please check your connection and try again.', true);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Send enquiry';
    }
  });
}
