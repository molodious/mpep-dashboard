/**
 * MPEP Dashboard — Shared Auth Layer
 * Password: mpep2026  (change by updating HASH below + redeploying)
 * Uses SHA-256 via Web Crypto API. Persists login in localStorage.
 */

const AUTH_KEY  = 'mpep_auth_v1';
const HASH      = 'c67ebe487dd9063713319a088f8f27732678bdee2a8ccc2670856cfdaf11fe5d';

async function sha256(str) {
  const buf  = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('');
}

function isAuthenticated() {
  return localStorage.getItem(AUTH_KEY) === HASH;
}

function logout() {
  localStorage.removeItem(AUTH_KEY);
  location.reload();
}

async function handleLogin(e) {
  e.preventDefault();
  const input = document.getElementById('pwd-input');
  const err   = document.getElementById('pwd-error');
  const btn   = document.getElementById('pwd-btn');

  btn.textContent = 'Checking…';
  btn.disabled = true;

  const h = await sha256(input.value.trim());

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

  // Hide main content until authenticated
  const main = document.getElementById('main-content');
  if (main) main.style.display = 'none';

  // Show overlay
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
