/**
 * MPEP Dashboard — Shared Auth Layer
 * Password: mpep2026  (change by updating HASH below + redeploying)
 * Uses a pure-JS SHA-256 (no crypto.subtle required — works on HTTP too).
 */

const AUTH_KEY = 'mpep_auth_v1';
const HASH     = 'c67ebe487dd9063713319a088f8f27732678bdee2a8ccc2670856cfdaf11fe5d';

// ── Pure-JS SHA-256 (works on HTTP + all browsers) ────────────────────────
function sha256(str) {
  function rr(v, a) { return (v >>> a) | (v << (32 - a)); }
  const pw = Math.pow, mw = pw(2, 32);
  let i, j, result = '', words = [], h = sha256._h || [], k = sha256._k || [];
  if (!sha256._h) {
    let pc = 0;
    const ic = {};
    for (let c = 2; pc < 64; c++) {
      if (!ic[c]) {
        for (i = 0; i < 313; i += c) ic[i] = c;
        h[pc]   = (pw(c, 0.5) * mw) | 0;
        k[pc++] = (pw(c, 1/3) * mw) | 0;
      }
    }
    sha256._h = h; sha256._k = k;
  }
  let ascii = str + '\x80';
  while (ascii.length % 64 - 56) ascii += '\x00';
  const abl = str.length * 8;
  for (i = 0; i < ascii.length; i++) {
    j = ascii.charCodeAt(i);
    words[i >> 2] |= j << ((3 - i % 4) * 8);
  }
  words.push((abl / mw) | 0);
  words.push(abl >>> 0);
  let hash = h.slice(0, 8);
  for (j = 0; j < words.length; j += 16) {
    const w = words.slice(j, j + 16);
    const oh = hash.slice();
    for (i = 0; i < 64; i++) {
      const w15 = w[i-15]|0, w2 = w[i-2]|0;
      const [a,,,,e] = hash;
      const t1 = hash[7]
        + (rr(e,6)^rr(e,11)^rr(e,25))
        + ((e & hash[5]) ^ (~e & hash[6]))
        + k[i]
        + (w[i] = i < 16 ? w[i]|0 :
            (w[i-16] + (rr(w15,7)^rr(w15,18)^(w15>>>3)) + w[i-7] + (rr(w2,17)^rr(w2,19)^(w2>>>10))) | 0);
      const t2 = (rr(a,2)^rr(a,13)^rr(a,22)) + ((a&hash[1])^(a&hash[2])^(hash[1]&hash[2]));
      hash = [(t1+t2)|0, ...hash];
      hash[4] = (hash[4] + t1) | 0;
      hash.length = 8;
    }
    hash = hash.map((v, i) => (v + oh[i]) | 0);
  }
  for (i = 0; i < 8; i++)
    for (j = 3; j >= 0; j--) {
      const b = (hash[i] >> (j * 8)) & 255;
      result += (b < 16 ? '0' : '') + b.toString(16);
    }
  return result;
}
// ─────────────────────────────────────────────────────────────────────────────

function isAuthenticated() {
  return localStorage.getItem(AUTH_KEY) === HASH;
}

function logout() {
  localStorage.removeItem(AUTH_KEY);
  location.reload();
}

function handleLogin(e) {
  e.preventDefault();
  const input = document.getElementById('pwd-input');
  const err   = document.getElementById('pwd-error');
  const btn   = document.getElementById('pwd-btn');

  btn.textContent = 'Checking…';
  btn.disabled = true;

  try {
    const h = sha256(input.value.trim());
    if (h === HASH) {
      localStorage.setItem(AUTH_KEY, HASH);
      document.getElementById('auth-overlay').remove();
      document.getElementById('main-content').style.display = '';
      if (typeof onAuthenticated === 'function') onAuthenticated();
    } else {
      err.textContent = 'Incorrect password. Try again.';
      err.style.display = 'block';
      input.value = '';
      input.focus();
      btn.textContent = 'Unlock';
      btn.disabled = false;
    }
  } catch (ex) {
    err.textContent = 'Something went wrong. Please refresh and try again.';
    err.style.display = 'block';
    btn.textContent = 'Unlock';
    btn.disabled = false;
  }
}

function initAuth() {
  if (isAuthenticated()) {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) overlay.remove();
    const main = document.getElementById('main-content');
    if (main) main.style.display = '';
    if (typeof onAuthenticated === 'function') onAuthenticated();
    return;
  }
  const main = document.getElementById('main-content');
  if (main) main.style.display = 'none';
  const overlay = document.getElementById('auth-overlay');
  if (overlay) {
    overlay.style.display = 'flex';
    const form = document.getElementById('auth-form');
    if (form) form.addEventListener('submit', handleLogin);
    const input = document.getElementById('pwd-input');
    if (input) input.focus();
  }
}

document.addEventListener('DOMContentLoaded', initAuth);
