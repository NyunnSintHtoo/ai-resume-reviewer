"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Nav from "@/components/Nav";
import { getReview, submitReviewPdf, submitReviewText } from "@/lib/api";

type Phase = "idle" | "submitting" | "polling" | "failed";

const PROGRESS_MESSAGES = [
  "Reading your resume…",
  "Pulling up our best hiring guidance…",
  "Reviewing section by section…",
  "Double-checking the feedback…",
];

export default function SubmitPage() {
  const [tab, setTab] = useState<"upload" | "paste">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [resumeText, setResumeText] = useState("");
  const [jd, setJd] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [messageIdx, setMessageIdx] = useState(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (phase !== "polling") return;
    const t = setInterval(
      () => setMessageIdx((i) => (i + 1) % PROGRESS_MESSAGES.length),
      2200,
    );
    return () => clearInterval(t);
  }, [phase]);

  function pickFile(f: File | null) {
    if (f && !f.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function poll(id: string) {
    setPhase("polling");
    for (;;) {
      const review = await getReview(id);
      if (review.status === "completed") {
        router.push(`/review/${id}`);
        return;
      }
      if (review.status === "failed") {
        setError(review.error ?? "The review failed. Please try again.");
        setPhase("failed");
        return;
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (tab === "upload" && !file) {
      setError("Drop in a PDF or switch to pasting text.");
      return;
    }
    if (tab === "paste" && resumeText.trim().length < 50) {
      setError("Paste at least a few lines of your resume (50+ characters).");
      return;
    }

    setPhase("submitting");
    try {
      const jdOrNull = jd.trim() ? jd.trim() : null;
      const review =
        tab === "upload"
          ? await submitReviewPdf(file as File, jdOrNull)
          : await submitReviewText(resumeText.trim(), jdOrNull);
      if (review.status === "completed") {
        router.push(`/review/${review.id}`); // cache hit — instant
        return;
      }
      await poll(review.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setPhase("failed");
    }
  }

  const busy = phase === "submitting" || phase === "polling";

  return (
    <div>
      <Nav />
      <main className="mx-auto max-w-3xl px-6 py-14">
        <h1 className="text-4xl font-extrabold tracking-tight">
          Let&apos;s look at your resume
        </h1>
        <p className="mt-2 font-medium text-smoke">
          Upload a PDF or paste the text. Add a target job description for a
          keyword-match analysis.
        </p>

        {busy ? (
          <div className="mt-10 rounded-2xl border border-soft bg-white p-12 text-center shadow-soft">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-4 border-teal-wash border-t-teal" />
            <p className="mt-6 text-lg font-extrabold tracking-tight">
              {PROGRESS_MESSAGES[messageIdx]}
            </p>
            <p className="mt-2 text-sm font-medium text-smoke">
              This usually takes a few seconds. Hang tight!
            </p>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="mt-10 space-y-6">
            {/* Tabs */}
            <div className="inline-flex rounded-full border border-soft bg-white p-1 shadow-soft">
              {(["upload", "paste"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  className={`rounded-full px-5 py-2 text-sm font-bold transition ${
                    tab === t
                      ? "bg-teal text-white"
                      : "text-smoke hover:text-ink"
                  }`}
                >
                  {t === "upload" ? "Upload PDF" : "Paste text"}
                </button>
              ))}
            </div>

            {tab === "upload" ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  pickFile(e.dataTransfer.files[0] ?? null);
                }}
                onClick={() => fileInput.current?.click()}
                className={`cursor-pointer rounded-2xl border-2 border-dashed bg-white p-12 text-center shadow-soft transition ${
                  dragOver
                    ? "border-teal bg-teal-wash"
                    : "border-[rgba(41,37,36,0.15)] hover:border-teal"
                }`}
              >
                <input
                  ref={fileInput}
                  type="file"
                  accept="application/pdf,.pdf"
                  className="hidden"
                  onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
                />
                <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-teal-wash text-3xl">
                  📄
                </div>
                {file ? (
                  <>
                    <p className="mt-4 font-extrabold tracking-tight">
                      {file.name}
                    </p>
                    <p className="mt-1 text-sm font-medium text-smoke">
                      {(file.size / 1024).toFixed(0)} KB — click to choose a
                      different file
                    </p>
                  </>
                ) : (
                  <>
                    <p className="mt-4 font-extrabold tracking-tight">
                      Drag &amp; drop your resume PDF here
                    </p>
                    <p className="mt-1 text-sm font-medium text-smoke">
                      or click to browse — 5 MB max
                    </p>
                  </>
                )}
              </div>
            ) : (
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                rows={12}
                placeholder={
                  "Jane Doe\njane@example.com\n\nExperience\n- Built a REST API serving 2M requests/day…"
                }
                className="w-full rounded-2xl border border-soft bg-white p-5 text-sm font-medium leading-relaxed shadow-soft outline-none transition focus:border-teal"
              />
            )}

            <div>
              <label className="mb-1.5 block text-sm font-bold" htmlFor="jd">
                Target job description{" "}
                <span className="font-semibold text-mist">(optional)</span>
              </label>
              <textarea
                id="jd"
                value={jd}
                onChange={(e) => setJd(e.target.value)}
                rows={5}
                placeholder="Paste the job posting you're aiming for to get keyword-match analysis…"
                className="w-full rounded-2xl border border-soft bg-white p-5 text-sm font-medium leading-relaxed shadow-soft outline-none transition focus:border-teal"
              />
            </div>

            {error && (
              <p className="rounded-2xl bg-crit-wash px-4 py-3 text-sm font-semibold text-crit">
                {error}
              </p>
            )}

            <button
              type="submit"
              className="w-full rounded-full bg-teal py-4 text-base font-bold text-white shadow-lift transition hover:bg-teal-hover"
            >
              Review my resume
            </button>
          </form>
        )}
      </main>
    </div>
  );
}
