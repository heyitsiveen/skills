/**
 * Put an unpublished theme's preview cookie in a running Chrome's jar, before
 * Lighthouse takes a Sample in that Chrome.
 *
 *   node jar.mjs --port <debugging port> --store <store URL>
 *
 * The cookie, `_shopify_essential=<value>`, arrives on stdin. Lighthouse opens
 * its page in the browser's default context, so the cookie goes there, for the
 * store's host only. Prints `JAR <host>` once the jar holds it.
 */

import { connect, guarded, options, putPreviewCookie, readStdin } from './preview.mjs';

await guarded(async () => {
  const { port, store } = options(process.argv.slice(2), ['port', 'store']);
  const cookie = (await readStdin()).trim();
  const browser = await connect(port);
  try {
    await putPreviewCookie(browser, store, cookie);
  } finally {
    await browser.disconnect();
  }
  process.stdout.write(`JAR ${new URL(store).hostname}\n`);
});
