# Zero Slop website

The public site for [Zero Slop](https://github.com/manavmishra/ZeroSlop), built
with React, vinext, and Cloudflare Workers.

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
npm run build
PORT=3002 npm start
npm run test:e2e
```

The browser suite covers the install journey, clipboard interaction, FAQ,
mobile overflow, light and dark themes, reduced motion, and console errors.

## Hosting

The site builds for Cloudflare Workers through vinext. Its Sites project ID and
optional bindings live in `.openai/hosting.json`.
