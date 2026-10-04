## Local tool routing

In this plugin, run local checks through the declared `zero-slop-local` MCP
server. The examples below name its tools. Supply the contents of the named
drafts and packets using each tool's advertised input schema; never pass a file
path or run these examples through a shell. Example flags describe the matching
operation, not a command to execute. Save returned output only with the host's
approved file tools when the user requests a file.

Keep every editorial role and verification requirement below. A tool result
does not replace contextual reading or independent review. Learning still needs
affirmative consent, and activation needs separate consent. Use the `version`
tool with `check_for_updates: true` for the optional metadata-only release check.
Never call the remote editing tool automatically. If a local tool is unavailable,
use the documented manual path and disclose which checks did not run.

Do not delegate file conversion to other skills or execute shell commands,
custom scripts, or conversion programs outside the declared MCP servers.
For DOCX and PDF, use only built-in host file operations that support the format
without launching custom code. If those operations are unavailable, leave the
original file untouched, explain the format limitation, and ask the user to
provide the prose or approve a plain-text alternative. Never claim that styles,
layout, or the original format were preserved without producing that output.
