# Zero Slop website

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
