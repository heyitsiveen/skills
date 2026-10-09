/**
 * What the two Node programs that drive the invocation's Chrome share:
 * jar.mjs, run before each Lighthouse Sample, and smoke.mjs, the smoke checker.
 *
 * The decision program starts Chrome itself, with a throwaway profile and a
 * debugging port, and stops it by its pid. These programs only connect to it,
 * and disconnect without closing it.
 *
 * A theme's preview cookie goes into the browser's cookie jar for the store's
 * host only. From there Chrome sends it with every request to the store and
 * with no request to any other site, and a cookie the page sets later joins
 * it rather than replacing it. The cookie arrives on stdin, so it never
 * appears in a process list, a file or a log.
 *
 * puppeteer-core is installed in the invocation's temp workspace, not beside
 * this file, so it is loaded from the project SPEED_TUNE_NODE_PROJECT names.
 */

import { createRequire } from 'node:module';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export async function loadPuppeteer() {
  const project = process.env.SPEED_TUNE_NODE_PROJECT;
  if (!project) {
    throw new Error('SPEED_TUNE_NODE_PROJECT does not name the workspace project holding puppeteer-core');
  }
  const require = createRequire(join(project, 'package.json'));
  const entry = require.resolve('puppeteer-core');
  return (await import(pathToFileURL(entry).href)).default;
}

export async function connect(port) {
  const puppeteer = await loadPuppeteer();
  return puppeteer.connect({ browserURL: `http://127.0.0.1:${port}`, defaultViewport: null });
}

/**
 * Put `cookie` (`name=value`) in the jar of one browser context, as a host-only
 * cookie of the store: `url` without `domain`, the way Shopify itself sets it.
 * Reads the jar back and throws unless the cookie is there for that host alone.
 */
export async function putPreviewCookie(browser, storeUrl, cookie, contextId) {
  const cut = cookie.indexOf('=');
  if (cut < 1) {
    throw new Error('the preview cookie is not a name=value pair');
  }
  const name = cookie.slice(0, cut).trim();
  const value = cookie.slice(cut + 1).trim();
  const store = new URL('/', storeUrl);
  const scope = contextId ? { browserContextId: contextId } : {};
  const session = await browser.target().createCDPSession();
  try {
    await session.send('Storage.setCookies', {
      ...scope,
      cookies: [{
        name, value, url: store.href, path: '/', secure: true, httpOnly: true, sameSite: 'Lax',
      }],
    });
    const { cookies } = await session.send('Storage.getCookies', scope);
    const held = cookies.filter((c) => c.name === name);
    if (held.length !== 1 || held[0].value !== value || held[0].domain !== store.hostname) {
      throw new Error(`the jar does not hold ${name} for ${store.hostname} alone`);
    }
  } finally {
    await session.detach().catch(() => {});
  }
}

export async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf8');
}

/** `--name value` pairs into an object; each name in `required` must be present. */
export function options(argv, required) {
  const out = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i].startsWith('--') || i + 1 >= argv.length) {
      throw new Error(`unexpected argument ${argv[i]}`);
    }
    out[argv[i].slice(2)] = argv[i + 1];
  }
  for (const name of required) {
    if (!out[name]) {
      throw new Error(`--${name} is required`);
    }
  }
  return out;
}

/** Run `main`, and on failure print one line to stderr and exit 1. Never prints a cookie. */
export async function guarded(main) {
  try {
    await main();
  } catch (error) {
    process.stderr.write(`${error && error.message ? error.message : error}\n`);
    process.exit(1);
  }
}
