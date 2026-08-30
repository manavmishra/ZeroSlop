# Zero Slop website

> [!CAUTION]
> **This is not the live site.** zero-slop.ai is built from a separate repository,
> [ZSWebpage](https://github.com/manavmishra/ZSWebpage), checked out locally at
> `~/Documents/ChatGPT/ZSWEBSITE/ZSWebpage`. This directory is an older iteration:
> it still uses the grey `#f3f4ef` paper instead of production's pastel `#faf5e0`,
> and it builds one page where the live site serves fourteen. Deploying from here
> overwrote production once. `npm run deploy:cloudflare` now refuses; do not
> restore the old wrangler command. Edit the site in ZSWebpage.

The public site for [Zero Slop](https://github.com/manavmishra/ZeroSlop), built
with React and vinext, then exported as a static Cloudflare Pages site.

## Run it locally

Use Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

## Quality checks

```bash
npm test
npm run lint

# Start the production server before the browser suite.
npm run build:static
python3 -m http.server 3002 --directory dist/static
npm run test:e2e
```

The browser suite covers the install journey, clipboard interaction, FAQ,
mobile overflow, light and dark themes, reduced motion, and console errors.

## Hosting

`npm run build:static` writes the deployable site to `dist/static`. The export
keeps the structured data and small interaction scripts while removing the
framework runtime from the page.

Deploy the production artifact to the `zero-slop` Cloudflare Pages project:

```bash
npm run deploy:cloudflare
```

Cloudflare serves the immutable assets with the cache rules in
`public/_headers`. Custom domains are configured on the Pages project after the
`zero-slop.ai` DNS zone is active in Cloudflare.
