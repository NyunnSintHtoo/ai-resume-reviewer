import Link from "next/link";
import Nav from "@/components/Nav";

const FEATURES = [
  {
    title: "Grounded feedback",
    body: "Every suggestion is backed by a curated knowledge base of hiring guides and real job descriptions — not vibes.",
    icon: "📚",
  },
  {
    title: "Bullet rewrites",
    body: "See your weakest bullets rewritten side-by-side, with the reasoning behind each change spelled out.",
    icon: "✍️",
  },
  {
    title: "Job-match scoring",
    body: "Paste a target job description and get a keyword match ratio plus the exact terms you're missing.",
    icon: "🎯",
  },
];

const STEPS = [
  { step: "1", title: "Upload", body: "Drop in a PDF or paste your resume text." },
  { step: "2", title: "Analyze", body: "An agentic pipeline parses, retrieves guidance, reviews, and validates." },
  { step: "3", title: "Improve", body: "Get a score, section feedback, and concrete rewrites in seconds." },
];

export default function LandingPage() {
  return (
    <div>
      <Nav />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full opacity-25 blur-3xl"
          style={{
            background:
              "radial-gradient(closest-side, #14b8a6 0%, #d97706 70%, transparent 100%)",
          }}
        />
        <div className="relative mx-auto max-w-4xl px-6 pb-20 pt-24 text-center">
          <span
            className="inline-block rounded-full p-[1.5px]"
            style={{ background: "linear-gradient(90deg, #0d9488, #d97706)" }}
          >
            <span className="block rounded-full bg-white px-4 py-1.5 text-xs font-bold text-smoke">
              Powered by an agentic Claude workflow
            </span>
          </span>
          <h1 className="mt-6 text-5xl font-extrabold leading-[1.1] tracking-tight sm:text-6xl">
            Your resume, reviewed like a{" "}
            <span className="text-teal">friendly recruiter</span> would.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg font-medium text-smoke">
            Upload your resume, optionally add a target job description, and get
            a scored, section-by-section review with concrete bullet rewrites —
            grounded in real hiring guidance.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              href="/submit"
              className="rounded-full bg-teal px-8 py-4 text-base font-bold text-white shadow-lift transition hover:bg-teal-hover"
            >
              Review my resume
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full border border-soft bg-white px-8 py-4 text-base font-bold text-ink shadow-soft transition hover:shadow-lift"
            >
              See my history
            </Link>
          </div>
          <p className="mt-4 text-sm font-medium text-mist">
            No sign-up needed — jump straight in.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 pb-20">
        <div className="grid gap-6 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-soft bg-white p-8 shadow-soft transition hover:shadow-lift"
            >
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-teal-wash text-2xl">
                {f.icon}
              </div>
              <h3 className="mt-5 text-lg font-extrabold tracking-tight">
                {f.title}
              </h3>
              <p className="mt-2 text-sm font-medium leading-relaxed text-smoke">
                {f.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="rounded-2xl border border-soft bg-white p-10 shadow-soft">
          <h2 className="text-center text-2xl font-extrabold tracking-tight">
            How it works
          </h2>
          <div className="mt-8 grid gap-8 sm:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.step} className="text-center">
                <div className="mx-auto grid h-10 w-10 place-items-center rounded-full bg-amber-wash text-sm font-extrabold text-amber">
                  {s.step}
                </div>
                <h3 className="mt-3 font-extrabold tracking-tight">{s.title}</h3>
                <p className="mt-1 text-sm font-medium text-smoke">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-soft py-8 text-center text-sm font-medium text-mist">
        Resumate — a full-stack portfolio project. FastAPI · Next.js · Claude ·
        local RAG.
      </footer>
    </div>
  );
}
