/**
 * The smoke checker: does each page still work on the Working theme the way it
 * does on the Control theme?
 *
 *   node smoke.mjs --port <debugging port> --spec <spec.json> --out <results.json>
 *
 * The spec names the store, the three pages' URLs and the two themes' ids. The
 * preview cookies arrive on stdin as {"control": "<cookie>", "working": "<cookie>"}
 * and are written nowhere.
 *
 * Each page is loaded on each theme in a fresh browser context whose jar holds
 * only that theme's preview cookie, on Lighthouse's emulated phone. It records:
 *
 *   load         the page answered HTTP 200
 *   menu-open    Tab reaches the header's menu button and Enter opens the menu
 *   menu-close   Escape closes it again
 *   variant      (product) choosing another option changes the form's variant
 *   add-to-cart  (product) the add button raises the cart's item count
 *   cart-count   (product) the header's cart count rises with it
 *
 * plus the app blocks present, the console errors, any Liquid error text, and
 * the theme the store rendered each same-origin response with. Each check is
 * pass, fail or skip (not applicable), with a short detail.
 *
 * It judges nothing: the decision program compares the two themes.
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { connect, guarded, options, putPreviewCookie, readStdin } from './preview.mjs';

const PAGES = ['home', 'collection', 'product'];
const ROLES = ['control', 'working'];
// Lighthouse's mobile device: a Moto G Power at 412x823, 1.75x.
const PHONE = { width: 412, height: 823, deviceScaleFactor: 1.75, isMobile: true, hasTouch: true };
const MAX_ERRORS = 50;
const MAX_TEXT = 300;
const TAB_LIMIT = 60;

const pass = (detail) => (detail ? { status: 'pass', detail } : { status: 'pass' });
const fail = (detail) => ({ status: 'fail', detail });
const skip = (detail) => ({ status: 'skip', detail });
const sleep = (ms) => new Promise((resolve) => { setTimeout(resolve, ms); });
const clip = (text) => String(text ?? '').replace(/\s+/g, ' ').trim().slice(0, MAX_TEXT);

function themeIn(serverTiming) {
  const found = /theme;desc="?(\d+)"?/.exec(serverTiming || '');
  return found ? Number(found[1]) : null;
}

function mobileAgent(version) {
  const major = (/\/(\d+)\./.exec(version) || [])[1] || '154';
  return 'Mozilla/5.0 (Linux; Android 11; moto g power (2022)) AppleWebKit/537.36 '
    + `(KHTML, like Gecko) Chrome/${major}.0.0.0 Mobile Safari/537.36`;
}

await guarded(async () => {
  const opts = options(process.argv.slice(2), ['port', 'spec', 'out']);
  const spec = JSON.parse(readFileSync(opts.spec, 'utf8'));
  const cookies = JSON.parse(await readStdin());
  const browser = await connect(opts.port);
  const results = { checker: 1, browser: await browser.version(), pages: {} };
  try {
    for (const name of PAGES) {
      results.pages[name] = {};
      for (const role of ROLES) {
        results.pages[name][role] = await checkPage(browser, spec, name, role, cookies[role]);
      }
    }
  } finally {
    await browser.disconnect();
  }
  writeFileSync(opts.out, `${JSON.stringify(results, null, 1)}\n`);
});

async function checkPage(browser, spec, name, role, cookie) {
  const url = spec.pages[name];
  const host = new URL(spec.store).hostname;
  const run = {
    url, status: null, theme: null, served_by: {}, preview_bar: false,
    checks: {}, app_blocks: [], console_errors: [], liquid_errors: [],
  };
  const context = await browser.createBrowserContext();
  try {
    await putPreviewCookie(browser, spec.store, cookie, context.id);
    const page = await context.newPage();
    await page.setViewport(PHONE);
    await page.setUserAgent(mobileAgent(await browser.version()));
    watch(page, run, host);

    let response;
    try {
      response = await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    } catch (error) {
      run.checks.load = fail(`did not load: ${clip(error.message)}`);
      return run;
    }
    run.status = response ? response.status() : null;
    run.theme = themeIn(response && response.headers()['server-timing'])
      ?? await page.evaluate(() => (window.Shopify && window.Shopify.theme ? window.Shopify.theme.id : null));
    const served = response ? await response.text().catch(() => '') : '';
    await page.waitForNetworkIdle({ idleTime: 1000, timeout: 15000 }).catch(() => {});
    run.checks.load = run.status === 200 ? pass() : fail(`HTTP ${run.status}`);
    await page.evaluate(installHelpers);
    run.app_blocks = await page.evaluate(() => [...document.querySelectorAll('.shopify-app-block')]
      .map((el) => el.id || el.getAttribute('class')));

    await guard(run, ['menu-open', 'menu-close'], () => checkMenu(page));
    if (name === 'product') {
      await guard(run, ['variant'], () => checkVariant(page));
      await guard(run, ['add-to-cart', 'cart-count'], () => checkAddToCart(page));
    }
    const rendered = await page.content().catch(() => '');
    run.liquid_errors = liquidErrors(`${served}\n${rendered}`);
    return run;
  } finally {
    await context.close().catch(() => {});
  }
}

/** A check that throws fails, rather than vanishing from the results. */
async function guard(run, names, check) {
  try {
    Object.assign(run.checks, await check());
  } catch (error) {
    for (const name of names) {
      if (!run.checks[name]) {
        run.checks[name] = fail(`the check broke: ${clip(error.message)}`);
      }
    }
  }
}

function watch(page, run, host) {
  const record = (text, url) => {
    if (run.console_errors.length < MAX_ERRORS) {
      run.console_errors.push({ text: clip(text), url: clip(url) });
    }
  };
  page.on('console', (message) => {
    if (message.type() === 'error') {
      record(message.text(), (message.location() || {}).url || '');
    }
  });
  page.on('pageerror', (error) => {
    record(`Uncaught ${error && error.message ? error.message : error}`, '');
  });
  page.on('request', (request) => {
    if (request.url().includes('/preview-bar/')) {
      run.preview_bar = true;
    }
  });
  page.on('response', (response) => {
    let responseHost;
    try {
      responseHost = new URL(response.url()).hostname;
    } catch {
      return;
    }
    const theme = responseHost === host ? themeIn(response.headers()['server-timing']) : null;
    if (theme) {
      run.served_by[theme] = (run.served_by[theme] || 0) + 1;
    }
  });
}

function liquidErrors(html) {
  const found = new Set();
  for (const match of html.matchAll(/Liquid (?:syntax )?error[^<\n]{0,240}/gi)) {
    found.add(clip(match[0]));
    if (found.size >= MAX_ERRORS) {
      break;
    }
  }
  return [...found];
}

/**
 * Runs in the page: the helpers the in-page checks share, on window.speedTuneSmoke.
 * Self-contained, because Puppeteer sends only a function's own source.
 */
function installHelpers() {
  const shown = (el) => el.checkVisibility({ visibilityProperty: true, opacityProperty: true });
  const onScreen = (el) => {
    const r = el.getBoundingClientRect();
    return r.width >= 1 && r.height >= 1 && r.bottom > 0 && r.right > 0
      && r.left < window.innerWidth && r.top < window.innerHeight;
  };
  window.speedTuneSmoke = {
    shown,
    onScreen,
    visibleFocusables() {
      return [...document.querySelectorAll('a[href], button, summary, input, select, textarea, [tabindex]')]
        .filter((el) => !el.closest('[inert]') && shown(el) && onScreen(el));
    },
    productForm() {
      const forms = [...document.querySelectorAll('form[action*="/cart/add"]')]
        .filter((form) => form.elements.namedItem('id'));
      return forms.find((form) => form.closest('main')) || forms[0] || null;
    },
    variantId() {
      const form = window.speedTuneSmoke.productForm();
      const field = form && form.elements.namedItem('id');
      return field ? String(field.value) : null;
    },
  };
}

/* ------------------------------------------------------------------ menu */

async function checkMenu(page) {
  const toggle = (await page.evaluateHandle(findMenuToggle)).asElement();
  if (!toggle) {
    return { 'menu-open': fail('no menu button in the header'), 'menu-close': skip('no menu button') };
  }
  const label = await toggle.evaluate(describe);
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    if (document.activeElement && document.activeElement !== document.body) {
      document.activeElement.blur();
    }
  });
  let reached = false;
  for (let presses = 0; presses < TAB_LIMIT && !reached; presses += 1) {
    await page.keyboard.press('Tab');
    reached = await toggle.evaluate((el) => el === document.activeElement || el.contains(document.activeElement));
  }
  if (!reached) {
    return {
      'menu-open': fail(`Tab did not reach ${label} in ${TAB_LIMIT} presses`),
      'menu-close': skip('the menu did not open'),
    };
  }
  await toggle.evaluate(rememberClosedMenu);
  await page.keyboard.press('Enter');
  if (!(await waitForMenu(toggle, true))) {
    return { 'menu-open': fail(`Enter on ${label} opened no menu`), 'menu-close': skip('the menu did not open') };
  }
  await page.keyboard.press('Escape');
  const closed = await waitForMenu(toggle, false);
  return {
    'menu-open': pass(label),
    'menu-close': closed ? pass() : fail('Escape left the menu open'),
  };
}

async function waitForMenu(toggle, open, limit = 3000) {
  const deadline = Date.now() + limit;
  while (Date.now() < deadline) {
    if ((await toggle.evaluate(menuLooksOpen)) === open) {
      return true;
    }
    await sleep(100);
  }
  return false;
}

/** Runs in the page: the header's visible control most likely to be the menu button. */
function findMenuToggle() {
  const { shown, onScreen } = window.speedTuneSmoke;
  const scopes = document.querySelectorAll('header, [role="banner"], .shopify-section-group-header-group');
  const seen = new Set();
  let best = null;
  let bestScore = 0;
  for (const scope of scopes) {
    for (const el of scope.querySelectorAll('button, summary, a[href], [role="button"], [aria-controls], [aria-expanded]')) {
      if (seen.has(el) || !shown(el) || !onScreen(el)) {
        continue;
      }
      seen.add(el);
      const own = [el.getAttribute('aria-label'), el.getAttribute('title'),
        (el.innerText || '').slice(0, 60)].join(' ');
      const around = [el, el.parentElement, el.parentElement && el.parentElement.parentElement]
        .map((node) => (node ? `${node.id} ${node.getAttribute('class') || ''}` : '')).join(' ');
      const words = `${own} ${around} ${el.getAttribute('aria-controls') || ''}`;
      if (!/menu|navigation|\bnav\b|hamburger|burger|drawer/i.test(words)
          || /cart|\bbag\b|basket|search|account|log ?in|sign ?in|wishlist|close|country|currency|language|locali[sz]/i.test(own)) {
        continue;
      }
      let score = 1;
      if (/menu|navigation/i.test(own)) score += 4;
      if (el.hasAttribute('aria-expanded') || el.hasAttribute('aria-controls') || el.tagName === 'SUMMARY') score += 2;
      if (el.tagName === 'BUTTON' || el.tagName === 'SUMMARY') score += 1;
      if (score > bestScore) {
        best = el;
        bestScore = score;
      }
    }
  }
  return best;
}

function describe(el) {
  const name = el.getAttribute('aria-label') || (el.innerText || '').trim().slice(0, 40)
    || el.getAttribute('class') || '';
  return `${el.tagName.toLowerCase()} "${name}"`;
}

/** Runs in the page: what was visible, and the toggle's own state, before Enter. */
function rememberClosedMenu(toggle) {
  const details = toggle.closest('details');
  window.speedTuneSmoke.menu = {
    visible: new Set(window.speedTuneSmoke.visibleFocusables()),
    expanded: toggle.getAttribute('aria-expanded'),
    details: details ? details.open : null,
  };
}

/** Runs in the page: open when the toggle says so, or when controls hidden before now show. */
function menuLooksOpen(toggle) {
  const before = window.speedTuneSmoke.menu;
  const details = toggle.closest('details');
  if (before.expanded !== 'true' && toggle.getAttribute('aria-expanded') === 'true') return true;
  if (before.details === false && details && details.open) return true;
  return window.speedTuneSmoke.visibleFocusables().filter((el) => !before.visible.has(el)).length >= 2;
}

/* --------------------------------------------------------------- product */

/** Runs in the page: choose another variant through the page's own option controls. */
async function chooseAnotherVariant() {
  const smoke = window.speedTuneSmoke;
  const result = (status, detail) => ({ variant: { status, detail } });
  const current = smoke.variantId();
  if (!current) {
    return result('fail', 'no add-to-cart form with a variant id');
  }
  let product;
  try {
    const response = await fetch(`${window.location.pathname.replace(/\/$/, '')}.js`,
      { credentials: 'same-origin' });
    product = await response.json();
  } catch (error) {
    return result('fail', `the product JSON did not load: ${error.message}`);
  }
  const variants = product.variants || [];
  if (variants.length < 2) {
    return result('skip', 'the product has one variant');
  }
  const now = variants.find((v) => String(v.id) === current) || variants[0];
  const differs = (v) => v.options.filter((value, i) => value !== now.options[i]).length;
  const target = variants
    .filter((v) => String(v.id) !== String(now.id))
    .sort((a, b) => (Number(b.available) - Number(a.available)) || (differs(a) - differs(b)))[0];
  const scope = document.querySelector('main') || document;
  for (let i = 0; i < target.options.length; i += 1) {
    const value = target.options[i];
    if (value === now.options[i]) {
      continue;
    }
    const radio = [...scope.querySelectorAll('input[type="radio"]')].find((el) => el.value === value);
    const select = [...scope.querySelectorAll('select')]
      .find((el) => [...el.options].some((option) => option.value === value));
    const ids = [...scope.querySelectorAll('select[name="id"]')]
      .find((el) => [...el.options].some((option) => option.value === String(target.id)));
    if (radio) {
      radio.click();
    } else if (select || ids) {
      const control = select || ids;
      control.value = select ? value : String(target.id);
      control.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      const option = (product.options[i] && product.options[i].name) || `option ${i + 1}`;
      return result('fail', `no control offers ${option} "${value}"`);
    }
  }
  const deadline = Date.now() + 6000;
  while (Date.now() < deadline) {
    if (smoke.variantId() === String(target.id)) {
      return result('pass', `${now.title} -> ${target.title}`);
    }
    await new Promise((resolve) => { setTimeout(resolve, 100); });
  }
  return result('fail', `the form still holds variant ${smoke.variantId()}, not ${target.title}`);
}

async function checkVariant(page) {
  return page.evaluate(chooseAnotherVariant);
}

async function cartItems(page) {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      return await page.evaluate(async () => {
        const response = await fetch('/cart.js', { credentials: 'same-origin', cache: 'no-store' });
        return (await response.json()).item_count;
      });
    } catch {
      await sleep(500); // the page may be navigating to the cart
    }
  }
  return null;
}

/** Runs in the page: the highest count a visible cart badge in the header shows; 0 for none. */
function headerCartCount() {
  const selector = '[data-cart-count], [data-cart-count-bubble], [class*="cart-count" i], '
    + '[class*="cartcount" i], [class*="cart_count" i], [class*="cart-item-count" i], '
    + '[id*="cart-count" i], [id*="cartcount" i], #cart-icon-bubble';
  let best = 0;
  for (const el of document.querySelectorAll(selector)) {
    if (!el.closest('header, [role="banner"], .shopify-section-group-header-group')) {
      continue;
    }
    for (const node of [el, ...el.querySelectorAll('*')]) {
      if (!node.checkVisibility({ visibilityProperty: true, opacityProperty: true })) {
        continue;
      }
      const found = /^(\d{1,3})\+?$/.exec((node.textContent || '').trim());
      if (found) {
        best = Math.max(best, Number(found[1]));
      }
    }
  }
  return best;
}

async function headerCount(page) {
  try {
    return await page.evaluate(headerCartCount);
  } catch {
    return null;
  }
}

/** Runs in the page: the product form's visible submit button. */
function findAddButton() {
  const form = window.speedTuneSmoke.productForm();
  if (!form) return null;
  const owned = form.id ? [...document.querySelectorAll(`[form="${CSS.escape(form.id)}"]`)] : [];
  return [...form.querySelectorAll('button, input[type="submit"]'), ...owned]
    .filter((el) => el.type === 'submit' || el.name === 'add')
    .find((el) => window.speedTuneSmoke.shown(el)) || null;
}

async function checkAddToCart(page) {
  const before = await cartItems(page);
  if (before === null) {
    return { 'add-to-cart': fail('/cart.js did not answer'), 'cart-count': skip('no cart to count') };
  }
  const shownBefore = await headerCount(page);
  const button = (await page.evaluateHandle(findAddButton)).asElement();
  if (!button) {
    return { 'add-to-cart': fail('no add-to-cart button'), 'cart-count': skip('nothing was added') };
  }
  if (await button.evaluate((el) => el.disabled || el.getAttribute('aria-disabled') === 'true')) {
    return { 'add-to-cart': fail('the add-to-cart button is disabled'), 'cart-count': skip('nothing was added') };
  }
  await button.click();

  let after = before;
  const deadline = Date.now() + 12000;
  while (Date.now() < deadline && !(after > before)) {
    await sleep(300);
    after = (await cartItems(page)) ?? after;
  }
  if (!(after > before)) {
    return {
      'add-to-cart': fail(`the cart still holds ${after} item(s)`),
      'cart-count': skip('nothing was added'),
    };
  }
  let shown = shownBefore ?? 0;
  const shownDeadline = Date.now() + 8000;
  while (Date.now() < shownDeadline && !(shown > (shownBefore ?? 0))) {
    await sleep(300);
    shown = (await headerCount(page)) ?? shown;
  }
  return {
    'add-to-cart': pass(`${before} -> ${after} item(s)`),
    'cart-count': shown > (shownBefore ?? 0) ? pass(`${shownBefore ?? 0} -> ${shown}`)
      : fail(`the header still shows ${shown}`),
  };
}
