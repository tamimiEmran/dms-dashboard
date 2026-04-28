/**
 * Dashboard password gate -- B-tier protection.
 *
 * Behavior:
 *   - On every HTML page load, check localStorage for a stored hash.
 *   - If the stored hash matches the embedded HASH constant, remove the
 *     hide-body style and let the page render normally.
 *   - Otherwise, replace <body> content with a centered password prompt.
 *     On correct password, store the hash and reload.
 *
 * The hide-body <style> is injected by the HTML's <head> (not by this
 * script) so the body is hidden BEFORE this script even fetches -- no
 * flash of original content.
 *
 * DOM is built via createElement (not innerHTML) so that any future edit
 * adding user-controlled text can't accidentally introduce XSS.
 *
 * Limitations (B-tier, see spec):
 *   - The full HTML is still in the HTTP response; curl bypasses the gate.
 *   - DevTools "delete the gate" bypass is accepted.
 *   - Asset URLs (assets/**) are not gated.
 */
(function () {
  'use strict';

  // SHA-256 of the shared password. Rotate by recomputing this hash and
  // committing the new value -- old localStorage entries auto-invalidate.
  const HASH = '07775f56063609b25c480986c5d51fc9127fc17197d1d7100b205e134a3bf8e0';
  const STORAGE_KEY = 'dms-dashboard-unlocked';
  const HIDE_STYLE_ID = 'dms-gate-hide';

  const hide = document.getElementById(HIDE_STYLE_ID);

  // Already unlocked -- reveal body and exit.
  if (localStorage.getItem(STORAGE_KEY) === HASH) {
    if (hide) hide.remove();
    return;
  }

  async function sha256(text) {
    const buf = await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(text)
    );
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }

  function buildPrompt() {
    const overlay = document.createElement('div');
    overlay.id = 'dms-gate';
    overlay.style.cssText =
      'position:fixed;inset:0;display:flex;align-items:center;' +
      'justify-content:center;background:#F8F9FB;' +
      'font-family:system-ui,-apple-system,sans-serif';

    const form = document.createElement('form');
    form.id = 'dms-gate-form';
    form.style.cssText =
      'display:flex;flex-direction:column;gap:12px;padding:32px;' +
      'background:#fff;border:1px solid #E0E2E8;border-radius:10px;' +
      'min-width:280px;box-shadow:0 4px 12px rgba(0,0,0,0.04)';

    const label = document.createElement('label');
    label.htmlFor = 'dms-gate-pw';
    label.textContent = 'Password';
    label.style.cssText = 'color:#5A5E6E;font-size:14px';

    const input = document.createElement('input');
    input.id = 'dms-gate-pw';
    input.type = 'password';
    input.autofocus = true;
    input.autocomplete = 'off';
    input.style.cssText =
      'padding:10px 12px;border:1px solid #E0E2E8;border-radius:6px;' +
      'font-size:14px;font-family:inherit;outline:none';

    const button = document.createElement('button');
    button.type = 'submit';
    button.textContent = 'Unlock';
    button.style.cssText =
      'padding:10px 12px;background:#0E9A7E;color:#fff;border:none;' +
      'border-radius:6px;font-size:14px;cursor:pointer;font-family:inherit';

    const msg = document.createElement('div');
    msg.id = 'dms-gate-msg';
    msg.style.cssText = 'color:#D9453E;font-size:13px;min-height:18px';

    form.appendChild(label);
    form.appendChild(input);
    form.appendChild(button);
    form.appendChild(msg);
    overlay.appendChild(form);

    return { overlay, form, input, msg };
  }

  function showPrompt() {
    // Clear body, then mount the prompt.
    while (document.body.firstChild) {
      document.body.removeChild(document.body.firstChild);
    }
    const { overlay, form, input, msg } = buildPrompt();
    document.body.appendChild(overlay);

    // Body now contains only the prompt; safe to remove the hide style.
    if (hide) hide.remove();

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const hash = await sha256(input.value);
      if (hash === HASH) {
        localStorage.setItem(STORAGE_KEY, HASH);
        location.reload();
      } else {
        msg.textContent = 'Wrong password.';
        input.value = '';
        input.focus();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showPrompt);
  } else {
    showPrompt();
  }
})();
