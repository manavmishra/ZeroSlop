# Zero Slop Writing Editor for Raycast

Select text in your app, open **Edit Selected Text**, and review the draft before
sending it to Zero Slop. The result shows the original, the edit, writing scores,
and any remaining warnings. Copy it, or confirm that you want to paste it into
your current selection.

## Use it

1. Select the passage you want to edit, then open the Raycast command.
2. Check the draft. Choose its writing type and, optionally, describe the reader.
3. Choose **Send to Zero Slop**. Review the result before copying or pasting.

If Raycast cannot read the selection, paste a draft into the form. Selection and
pasting may require macOS Accessibility permission. The extension never reads
the clipboard as a fallback, never changes the original automatically, and does
not enable background editing.

Drafts may contain up to 20,000 characters; the audience description may contain
up to 200. Limits count Unicode code points, not UTF-16 code units.
Supported writing types are general, social, email, research, and
professional. A score measures tracked writing patterns, not authorship or
truth. A returned edit with warnings is labelled **Review required**. Unchanged
results explain why the original was retained.

## What is sent and saved

**Send to Zero Slop** sends the displayed text, writing type, and optional
audience to `https://mcp.zero-slop.ai/mcp`. It uses the same client and editing
pipeline as `zero-slop deslop`; it does not call another model or require a
separate API key. Review the [privacy policy](https://zero-slop.ai/privacy/) and
[terms](https://zero-slop.ai/terms/) before sending confidential material.

The extension keeps drafts and results in memory. It does not save form drafts,
write a text history, or log the writing. **Copy Edit** uses Raycast's concealed
clipboard option. The extension cannot control clipboard managers or what the
destination app retains. Pasting requires an explicit confirmation.

Cancel stops waiting for the result. A request already received by the hosted
service may still finish. There are no automatic retries.

## Local development

Requires macOS, Raycast, and Node.js 22.22.2 or newer. The extension and lockfile
pin the shared client to the published `zero-slop@2.10.0` npm release.

```sh
cd integrations/raycast
npm ci
npm test
npm run typecheck
npm run build
npm run dev
```

The icon is the official 512 × 512 Zero Slop mark from this repository. Do not
replace it with a generated approximation.

## Store submission checklist

- Confirm the `author` field matches the publisher's Raycast username. A GitHub
  username alone does not establish the Raycast handle.
- Keep the committed `package-lock.json` with registry dependencies. Do not
  replace the shared client with a local `file:` dependency for submission.
- Run tests, type checking, `npm run lint`, and a distribution build.
- Test selection, missing Accessibility permission, cancellation, warnings, copy,
  and confirmed paste in Raycast. This extension currently declares macOS only.
- Capture real extension screenshots with Raycast's Window Capture. Recommended
  scenes: selected draft, a completed edit, and a warning result. Do not use
  invented screenshots or private writing.
- Run `npm run publish` to open the review pull request. The extension becomes
  listed only after Raycast accepts and merges it.

References: [Store preparation](https://developers.raycast.com/basics/prepare-an-extension-for-store),
[publication](https://developers.raycast.com/basics/publish-an-extension),
[selected text](https://developers.raycast.com/api-reference/environment#getselectedtext),
[clipboard behavior](https://developers.raycast.com/api-reference/clipboard).
