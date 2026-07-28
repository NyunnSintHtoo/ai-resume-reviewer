"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import Sparkline from "@/components/Sparkline";
import { getHistory } from "@/lib/api";
import type { ReviewListItem } from "@/lib/types";

export default function DashboardPage() {
  const [items, setItems] = useState<ReviewListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHistory()
      .then(setItems)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load history"),
      );
  }, []);

  const scores =
    items
      ?.filter((i) => i.overall_score != null)
      .slice()
      .reverse() // oldest -> newest
      .map((i) => i.overall_score as number) ?? [];

  const best = scores.length ? Math.max(...scores) : null;
  const latest = scores.length ? scores[scores.length - 1] : null;

  return (
    <div>
      <Nav />
      <main className="mx-auto max-w-5xl px-6 py-14">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight">
              Your dashboard
            </h1>
            <p className="mt-2 font-medium text-smoke">
              Every review you&apos;ve run, and how your score is trending.
            </p>
          </div>
          <Link
            href="/submit"
            className="rounded-full bg-teal px-6 py-3 font-bold text-white shadow-soft transition hover:bg-teal-hover"
          >
            New review
          </Link>
        </div>

        {error && (
          <p className="mt-8 rounded-2xl bg-crit-wash px-5 py-4 font-semibold text-crit">
            {error}
          </p>
        )}

        {items === null && !error && (
          <div className="mt-10 rounded-2xl border border-soft bg-white p-12 text-center shadow-soft">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-teal-wash border-t-teal" />
          </div>
        )}

        {items !== null && items.length === 0 && (
          <div className="mt-10 rounded-2xl border border-soft bg-white p-14 text-center shadow-soft">
            <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-teal-wash text-4xl">
              🌱
            </div>
            <h2 className="mt-5 text-xl font-extrabold tracking-tight">
              No reviews yet — let&apos;s change that!
            </h2>
            <p className="mx-auto mt-2 max-w-sm text-sm font-medium text-smoke">
              Run your first review and this page will start tracking your
              scores over time.
            </p>
            <Link
              href="/submit"
              className="mt-6 inline-block rounded-full bg-teal px-7 py-3 font-bold text-white shadow-soft transition hover:bg-teal-hover"
            >
              Review my resume
            </Link>
          </div>
        )}

        {items !== null && items.length > 0 && (
          <>
            {/* Trend card */}
            <section className="mt-10 rounded-2xl border border-soft bg-white p-8 shadow-soft">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <h2 className="font-extrabold tracking-tight">Score trend</h2>
                <div className="flex gap-6 text-sm font-medium text-smoke">
                  {latest != null && (
                    <span>
                      Latest{" "}
                      <span className="font-extrabold text-teal">
                        {Math.round(latest)}
                      </span>
                    </span>
                  )}
                  {best != null && (
                    <span>
                      Best{" "}
                      <span className="font-extrabold text-amber">
                        {Math.round(best)}
                      </span>
                    </span>
                  )}
                  <span>
                    Reviews{" "}
                    <span className="font-extrabold text-ink">
                      {items.length}
                    </span>
                  </span>
                </div>
              </div>
              {scores.length >= 2 ? (
                <div className="mt-6">
                  <Sparkline values={scores} />
                </div>
              ) : (
                <p className="mt-6 text-sm font-medium text-smoke">
                  Run a couple more reviews to see your trend line here.
                </p>
              )}
            </section>

            {/* History list */}
            <section className="mt-8 space-y-4 pb-16">
              {items.map((item) => (
                <Link
                  key={item.id}
                  href={`/review/${item.id}`}
                  className="flex items-center justify-between gap-4 rounded-2xl border border-soft bg-white p-6 shadow-soft transition hover:shadow-lift"
                >
                  <div className="min-w-0">
                    <p className="font-extrabold tracking-tight">
                      {new Date(item.created_at).toLocaleString(undefined, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </p>
                    <p className="mt-1 truncate text-sm font-medium text-smoke">
                      {item.job_description_preview
                        ? `Target role: ${item.job_description_preview}`
                        : "General review (no target job description)"}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-4">
                    <span className="rounded-full bg-cream px-3 py-1 text-xs font-bold text-smoke">
                      {item.provider}
                    </span>
                    {item.overall_score != null ? (
                      <span className="grid h-12 w-12 place-items-center rounded-full bg-teal-wash text-base font-extrabold text-teal">
                        {Math.round(item.overall_score)}
                      </span>
                    ) : (
                      <span className="rounded-full bg-amber-wash px-3 py-1 text-xs font-bold text-amber">
                        {item.status}
                      </span>
                    )}
                  </div>
                </Link>
              ))}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
