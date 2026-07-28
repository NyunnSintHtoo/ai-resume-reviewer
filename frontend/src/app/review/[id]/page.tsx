"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import ScoreRing from "@/components/ScoreRing";
import SeverityChip from "@/components/SeverityChip";
import { getReview } from "@/lib/api";
import type { ReviewStatusResponse } from "@/lib/types";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [review, setReview] = useState<ReviewStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        for (;;) {
          const r = await getReview(id);
          if (cancelled) return;
          setReview(r);
          if (r.status === "completed" || r.status === "failed") return;
          await new Promise((res) => setTimeout(res, 1500));
        }
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load review");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <Shell>
        <p className="rounded-2xl bg-crit-wash px-5 py-4 font-semibold text-crit">
          {error}
        </p>
      </Shell>
    );
  }

  if (!review || review.status === "pending" || review.status === "processing") {
    return (
      <Shell>
        <div className="rounded-2xl border border-soft bg-white p-12 text-center shadow-soft">
          <div className="mx-auto h-14 w-14 animate-spin rounded-full border-4 border-teal-wash border-t-teal" />
          <p className="mt-6 font-extrabold tracking-tight">
            Your review is being prepared…
          </p>
        </div>
      </Shell>
    );
  }

  if (review.status === "failed" || !review.result) {
    return (
      <Shell>
        <p className="rounded-2xl bg-crit-wash px-5 py-4 font-semibold text-crit">
          {review.error ?? "This review failed to complete."}
        </p>
      </Shell>
    );
  }

  const r = review.result;
  const hasJd = r.keywords.matched.length + r.keywords.missing.length > 0;

  return (
    <Shell>
      {/* Score card */}
      <section className="rounded-2xl border border-soft bg-white p-10 shadow-soft">
        <div className="flex flex-col items-center gap-8 sm:flex-row sm:gap-12">
          <ScoreRing score={r.overall_score} />
          <div className="flex-1 text-center sm:text-left">
            <p className="text-xs font-bold uppercase tracking-widest text-teal">
              Overall assessment · {review.provider} provider
            </p>
            <p className="mt-3 text-lg font-semibold leading-relaxed">
              {r.summary}
            </p>
            {r.strengths.length > 0 && (
              <ul className="mt-5 space-y-1.5 text-left">
                {r.strengths.map((s) => (
                  <li
                    key={s}
                    className="flex items-start gap-2 text-sm font-medium text-smoke"
                  >
                    <span className="mt-0.5 text-good">✓</span>
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {/* Section feedback */}
      <h2 className="mt-12 text-2xl font-extrabold tracking-tight">
        Section by section
      </h2>
      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        {r.sections.map((s) => (
          <div
            key={s.section}
            className="rounded-2xl border border-soft bg-white p-7 shadow-soft"
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-extrabold tracking-tight">{s.section}</h3>
              <SeverityChip severity={s.severity} />
            </div>
            <div className="mt-4 flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-cream">
                <div
                  className="h-full rounded-full bg-amber"
                  style={{ width: `${Math.min(100, s.score)}%` }}
                />
              </div>
              <span className="text-sm font-extrabold text-amber">
                {Math.round(s.score)}
              </span>
            </div>
            <p className="mt-4 text-sm font-medium leading-relaxed text-smoke">
              {s.feedback}
            </p>
            {s.suggestions.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {s.suggestions.map((sg) => (
                  <li
                    key={sg}
                    className="flex items-start gap-2 text-sm font-medium text-smoke"
                  >
                    <span className="mt-0.5 text-teal">→</span>
                    {sg}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      {/* Bullet rewrites */}
      {r.bullet_rewrites.length > 0 && (
        <>
          <h2 className="mt-12 text-2xl font-extrabold tracking-tight">
            Bullet rewrites
          </h2>
          <p className="mt-1 text-sm font-medium text-smoke">
            Your original bullet on the left, our suggested rewrite on the
            right.
          </p>
          <div className="mt-5 space-y-5">
            {r.bullet_rewrites.map((b, i) => (
              <div
                key={i}
                className="overflow-hidden rounded-2xl border border-soft bg-white shadow-soft"
              >
                <div className="grid sm:grid-cols-2">
                  <div className="border-b border-soft p-6 sm:border-b-0 sm:border-r">
                    <p className="text-xs font-bold uppercase tracking-widest text-mist">
                      Before
                    </p>
                    <p className="mt-2 text-sm font-medium leading-relaxed text-smoke">
                      {b.original}
                    </p>
                  </div>
                  <div className="bg-teal-wash p-6">
                    <p className="text-xs font-bold uppercase tracking-widest text-teal">
                      After
                    </p>
                    <p className="mt-2 text-sm font-semibold leading-relaxed text-ink">
                      {b.improved}
                    </p>
                  </div>
                </div>
                <p className="border-t border-soft px-6 py-3 text-xs font-medium text-smoke">
                  <span className="font-bold text-amber">Why:</span>{" "}
                  {b.rationale}
                </p>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Keyword match */}
      <h2 className="mt-12 text-2xl font-extrabold tracking-tight">
        Job description match
      </h2>
      <div className="mt-5 rounded-2xl border border-soft bg-white p-8 shadow-soft">
        {hasJd ? (
          <>
            <p className="font-semibold">
              Your resume matches{" "}
              <span className="rounded-full bg-amber-wash px-2.5 py-0.5 font-extrabold text-amber">
                {Math.round(r.keywords.match_ratio * 100)}%
              </span>{" "}
              of the key terms in the target role.
            </p>
            <div className="mt-6 grid gap-6 sm:grid-cols-2">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-good">
                  Matched ({r.keywords.matched.length})
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {r.keywords.matched.map((k) => (
                    <span
                      key={k}
                      className="rounded-full bg-good-wash px-3 py-1 text-xs font-bold text-good"
                    >
                      {k}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-amber">
                  Missing ({r.keywords.missing.length})
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {r.keywords.missing.map((k) => (
                    <span
                      key={k}
                      className="rounded-full bg-amber-wash px-3 py-1 text-xs font-bold text-amber"
                    >
                      {k}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <p className="text-sm font-medium text-smoke">
            No target job description was provided for this review. Submit
            again with one to see matched and missing keywords.
          </p>
        )}
      </div>

      {/* ATS notes */}
      {r.ats_notes.length > 0 && (
        <div className="mt-8 rounded-2xl border border-soft bg-white p-8 shadow-soft">
          <h3 className="font-extrabold tracking-tight">ATS notes</h3>
          <ul className="mt-3 space-y-1.5">
            {r.ats_notes.map((n) => (
              <li
                key={n}
                className="flex items-start gap-2 text-sm font-medium text-smoke"
              >
                <span className="mt-0.5 text-amber">•</span>
                {n}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-12 flex justify-center gap-4 pb-16">
        <Link
          href="/submit"
          className="rounded-full bg-teal px-7 py-3 font-bold text-white shadow-soft transition hover:bg-teal-hover"
        >
          Review another version
        </Link>
        <Link
          href="/dashboard"
          className="rounded-full border border-soft bg-white px-7 py-3 font-bold shadow-soft transition hover:shadow-lift"
        >
          Back to dashboard
        </Link>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <Nav />
      <main className="mx-auto max-w-5xl px-6 py-14">{children}</main>
    </div>
  );
}
