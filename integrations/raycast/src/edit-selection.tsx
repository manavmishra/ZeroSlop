import {
  Action,
  ActionPanel,
  Alert,
  Clipboard,
  Detail,
  Form,
  Icon,
  Toast,
  confirmAlert,
  getSelectedText,
  showToast,
} from "@raycast/api";
import { useEffect, useRef, useState } from "react";
import { deslop, isApprovedResult } from "zero-slop/bin/lib/deslop.mjs";
import {
  GENRES,
  STATUS_LABELS,
  editDraft,
  reviewMarkdown,
  validateDraft,
} from "./review";

type Result = Awaited<ReturnType<typeof deslop>>;

export default function Command() {
  const [text, setText] = useState("");
  const [genre, setGenre] = useState("general");
  const [audience, setAudience] = useState("");
  const [loadingSelection, setLoadingSelection] = useState(true);
  const [busy, setBusy] = useState(false);
  const [selectionNote, setSelectionNote] = useState("");
  const [error, setError] = useState<string>();
  const [result, setResult] = useState<Result>();
  const [original, setOriginal] = useState("");
  const request = useRef<AbortController | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    getSelectedText()
      .then((selection) => {
        if (mounted.current) setText(selection);
      })
      .catch(() => {
        if (mounted.current)
          setSelectionNote(
            "No selected text was available. Paste a draft below, or allow Raycast Accessibility access and select text in your app.",
          );
      })
      .finally(() => {
        if (mounted.current) setLoadingSelection(false);
      });
    return () => {
      mounted.current = false;
      request.current?.abort();
    };
  }, []);

  async function submit() {
    if (request.current || busy || loadingSelection) return;
    try {
      validateDraft(text, genre, audience);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Check your draft.");
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError(undefined);
    try {
      const next = await editDraft(
        text,
        genre,
        audience,
        controller.signal,
        deslop,
      );
      if (mounted.current && !controller.signal.aborted) {
        setOriginal(text.trim());
        setResult(next);
      }
    } catch (error) {
      if (mounted.current && !controller.signal.aborted) {
        await showToast({
          style: Toast.Style.Failure,
          title: "Could not complete edit",
          message:
            error instanceof Error ? error.message : "Please try again later.",
        });
      }
    } finally {
      if (mounted.current) setBusy(false);
      request.current = null;
    }
  }

  async function pasteResult() {
    if (!result) return;
    const accepted = await confirmAlert({
      title: "Paste edited text?",
      message: isApprovedResult(result)
        ? "This inserts the edit at the current selection in your frontmost app. Check that the intended text is still selected."
        : "This result needs your review. If you have checked it, paste it at the current selection in your frontmost app.",
      primaryAction: { title: "Paste Edit", style: Alert.ActionStyle.Default },
      dismissAction: { title: "Keep Reviewing" },
    });
    if (accepted) {
      try {
        await Clipboard.paste(result.text);
      } catch {
        await showToast({
          style: Toast.Style.Failure,
          title: "Could not paste",
          message: "Copy the edit and paste it in your app instead.",
        });
      }
    }
  }

  if (result) {
    return (
      <Detail
        navigationTitle="Review Zero Slop Edit"
        markdown={reviewMarkdown(original, result)}
        metadata={
          <Detail.Metadata>
            <Detail.Metadata.Label
              title="Result"
              text={STATUS_LABELS[result.status]}
            />
            <Detail.Metadata.Label
              title="Writing score"
              text={`${result.before.score} → ${result.after.score}`}
            />
            <Detail.Metadata.Label
              title="Facts retained"
              text={result.factsPreserved ? "Checked" : "Not confirmed"}
            />
            <Detail.Metadata.Label
              title="Final checks"
              text={
                result.status === "already_clear"
                  ? "No model edit needed"
                  : result.passedFinalChecks
                    ? "Passed"
                    : "Review required"
              }
            />
            <Detail.Metadata.Label
              title="Editing requests"
              text={String(result.modelRequests)}
            />
            <Detail.Metadata.Separator />
            <Detail.Metadata.Link
              title="Privacy"
              text="Zero Slop privacy policy"
              target="https://zero-slop.ai/privacy/"
            />
          </Detail.Metadata>
        }
        actions={
          <ActionPanel>
            <Action
              title="Copy Edit"
              icon={Icon.Clipboard}
              onAction={async () => {
                await Clipboard.copy(result.text, { concealed: true });
                await showToast({
                  style: Toast.Style.Success,
                  title: "Edit copied",
                });
              }}
            />
            <Action
              title="Paste Edit"
              icon={Icon.Document}
              onAction={pasteResult}
              shortcut={{ modifiers: ["cmd", "shift"], key: "v" }}
            />
            <Action
              title="Back to Draft"
              icon={Icon.ArrowLeft}
              onAction={() => setResult(undefined)}
            />
          </ActionPanel>
        }
      />
    );
  }

  return (
    <Form
      navigationTitle="Edit Selected Text"
      isLoading={loadingSelection || busy}
      actions={
        <ActionPanel>
          {!busy && (
            <Action.SubmitForm
              title="Send to Zero Slop"
              icon={Icon.Wand}
              onSubmit={submit}
            />
          )}
          {busy && (
            <Action
              title="Cancel Edit"
              icon={Icon.XMarkCircle}
              onAction={() => {
                request.current?.abort();
              }}
            />
          )}
          <Action.OpenInBrowser
            title="Read Privacy Policy"
            url="https://zero-slop.ai/privacy/"
          />
        </ActionPanel>
      }
    >
      <Form.Description
        title="Hosted editing"
        text="Send this draft to mcp.zero-slop.ai for editing. No account or API key is needed. Your text stays in memory in this extension; it is not saved as a Raycast draft or logged. Nothing is pasted automatically."
      />
      {selectionNote && <Form.Description text={selectionNote} />}
      <Form.TextArea
        id="text"
        title="Draft"
        value={text}
        onChange={(value) => {
          if (!busy) {
            setText(value);
            setError(undefined);
          }
        }}
        error={error}
        info="Up to 20,000 Unicode code points. Review confidential material before sending it to a hosted service."
      />
      <Form.Dropdown
        id="genre"
        title="Writing type"
        value={genre}
        onChange={(value) => {
          if (!busy) setGenre(value);
        }}
      >
        {GENRES.map((value) => (
          <Form.Dropdown.Item
            key={value}
            value={value}
            title={value.charAt(0).toUpperCase() + value.slice(1)}
          />
        ))}
      </Form.Dropdown>
      <Form.TextField
        id="audience"
        title="Audience"
        placeholder="Optional, e.g. engineering managers"
        value={audience}
        onChange={(value) => {
          if (!busy) setAudience(value);
        }}
      />
      {busy && (
        <Form.Description text="Editing and checking your draft. Cancel stops waiting; a request already received by the service may still finish." />
      )}
    </Form>
  );
}
