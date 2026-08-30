#!/usr/bin/env node
/**
 * This directory is NOT the source of zero-slop.ai. It is an older iteration.
 *
 * It used to carry `wrangler pages deploy ... --project-name=zero-slop
 * --branch=main`, which points straight at production. Running it overwrote the
 * live site with this stale build. That happened once; this guard exists so it
 * cannot happen again by muscle memory.
 *
 * The live site is a separate repository, github.com/manavmishra/ZSWebpage,
 * checked out locally at ~/Documents/ChatGPT/ZSWEBSITE/ZSWebpage.
 */
const RIGHT = "~/Documents/ChatGPT/ZSWEBSITE/ZSWebpage (github.com/manavmishra/ZSWebpage)";

console.error(`
  Refusing to deploy: this folder is not zero-slop.ai.

  You are in the ZeroSlop skill repo's website/ directory, an older iteration of
  the site. Its palette is still the grey #f3f4ef; production is the pastel
  #faf5e0. Deploying from here overwrites the live site with stale pages.

  Deploy from ${RIGHT} instead:

      cd ~/Documents/ChatGPT/ZSWEBSITE/ZSWebpage
      npm run build:static
      npx wrangler pages deploy dist/static --project-name=zero-slop --branch=main
`);
process.exit(1);
