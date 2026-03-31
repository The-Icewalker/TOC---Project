import { useState, useRef, useEffect } from "react";
import "./RegexTranslator.css";

// ─────────────────────────────────────────────────────────────
//  BACKEND URL — change this if Flask runs on a different port
// ─────────────────────────────────────────────────────────────
const API_URL = "https://toc-project-azwy.onrender.com/analyze";

async function parseRegex(pattern) {
  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ regex: pattern }),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return await res.json();
  // Returns: { regex, english, steps[], accepted[], rejected[], valid }
  //      or: { valid: false, error: "..." }
}
// ─────────────────────────────────────────────────────────────

const TEAM_MEMBERS = [
  { name: "Johith Babu S",    reg: "24BCE2452" },
  { name: "Bassil H",         reg: "24BCE0904" },
  { name: "Adarsh Menon",     reg: "24BAI0096" },
  { name: "Ajay Kumar Yadav", reg: "24BCE0805" },
];

export default function RegexTranslator() {
  const [input, setInput]         = useState("");
  const [result, setResult]       = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [animKey, setAnimKey]     = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    document.documentElement.style.cssText = "width:100%;height:100%;margin:0;padding:0;";
    document.body.style.cssText = "width:100%;min-height:100vh;margin:0;padding:0;background:#0e1f3d;";
    const root = document.getElementById("root");
    if (root) root.style.cssText = "width:100%;min-height:100vh;margin:0;padding:0;";
    return () => {
      document.documentElement.style.cssText = "";
      document.body.style.cssText = "";
      if (root) root.style.cssText = "";
    };
  }, []);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    setLoading(true);
    setError("");
    setResult(null);
    setSubmitted(true);
    try {
      const data = await parseRegex(trimmed);
      if (!data.valid) {
        setError(`Invalid regex: ${data.error}`);
      } else {
        setResult(data);
        setAnimKey((k) => k + 1);
      }
    } catch (err) {
      setError("Could not reach the backend. Is Flask running on port 5000?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => { if (e.key === "Enter") handleSubmit(e); };

  const handleClear = () => {
    setInput("");
    setResult(null);
    setError("");
    setSubmitted(false);
    inputRef.current?.focus();
  };

  return (
    <div className="rt-root">
      <div className="rt-bg-circle rt-bg-circle--1" />
      <div className="rt-bg-circle rt-bg-circle--2" />
      <div className="rt-bg-circle rt-bg-circle--3" />

      <main className="rt-shell">

        {/* ── HEADER ── */}
        <header className="rt-header">
          <div className="rt-header__badge">Theory of Computation</div>
          <h1 className="rt-header__title">
            <span className="rt-header__title-accent">RegEx</span>
            <br />Translator
          </h1>
          <p className="rt-header__sub">
            Paste any regular expression and receive a clear,<br />
            human-readable breakdown of what it matches.
          </p>
        </header>

        {/* ── INPUT CARD ── */}
        <section className="rt-card">
          <label className="rt-label" htmlFor="rt-input">Regular Expression</label>
          <div className="rt-input-row">
            <div className="rt-input-wrap">
              <span className="rt-input-slash">/</span>
              <input
                id="rt-input"
                ref={inputRef}
                className="rt-input"
                type="text"
                spellCheck={false}
                autoComplete="off"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g.  ^(a|b)*abb$"
              />
              <span className="rt-input-slash">/</span>
            </div>
            <button
              className="rt-btn rt-btn--primary"
              onClick={handleSubmit}
              disabled={loading || !input.trim()}
            >
              {loading ? <span className="rt-spinner" /> : (
                <><span className="rt-btn__text">Translate</span><span className="rt-btn__arrow">→</span></>
              )}
            </button>
            {submitted && (
              <button className="rt-btn rt-btn--ghost" onClick={handleClear}>Clear</button>
            )}
          </div>
          <p className="rt-hint">Press <kbd>Enter</kbd> or click Translate</p>
        </section>

        {/* ── OUTPUT AREA ── */}
        {(submitted || error) && (
          <div className="rt-results" key={animKey}>

            {error && <p className="rt-error">{error}</p>}

            {loading && (
              <section className="rt-output">
                <div className="rt-output__header">
                  <span className="rt-output__label">Analysing…</span>
                </div>
                <div className="rt-skeleton-list">
                  {[1,2,3,4].map(i => <div key={i} className="rt-skeleton" style={{"--i":i}} />)}
                </div>
              </section>
            )}

            {!loading && result && (
              <>
                {/* ENGLISH SUMMARY */}
                <section className="rt-output rt-output--summary">
                  <div className="rt-output__header">
                    <span className="rt-output__label">Summary</span>
                  </div>
                  <p className="rt-summary-text">{result.english}</p>
                </section>

                {/* STEP-BY-STEP */}
                <section className="rt-output">
                  <div className="rt-output__header">
                    <span className="rt-output__label">Step-by-Step Breakdown</span>
                  </div>
                  <ol className="rt-statements">
                    {result.steps.map((step, idx) => {
                      const arrowIdx = step.indexOf(" → ");
                      const token = arrowIdx !== -1 ? step.slice(0, arrowIdx) : step;
                      const desc  = arrowIdx !== -1 ? step.slice(arrowIdx + 3) : "";
                      return (
                        <li
                          key={idx}
                          className="rt-statement"
                          style={{ "--delay": `${idx * 60}ms` }}
                        >
                          <span className="rt-statement__num">{String(idx + 1).padStart(2, "0")}</span>
                          <span className="rt-statement__token">{token}</span>
                          <span className="rt-statement__arrow">→</span>
                          <span className="rt-statement__text">{desc}</span>
                        </li>
                      );
                    })}
                  </ol>
                </section>

                {/* ACCEPTED / REJECTED */}
                <div className="rt-strings-grid">
                  <section className="rt-output rt-output--accepted">
                    <div className="rt-output__header">
                      <span className="rt-output__label">✓ Few Accepted Strings</span>
                      
                    </div>
                    {result.accepted.length === 0
                      ? <p className="rt-empty">No matches found in samples</p>
                      : (
                        <ul className="rt-string-list">
                          {result.accepted.map((s, i) => (
                            <li key={i} className="rt-string-item rt-string-item--accepted"
                              style={{ "--delay": `${i * 60}ms` }}>
                              <span className="rt-string-tick">✓</span>
                              <code className="rt-string-val">"{s}"</code>
                            </li>
                          ))}
                        </ul>
                      )
                    }
                  </section>

                  <section className="rt-output rt-output--rejected">
                    <div className="rt-output__header">
                      <span className="rt-output__label">✗ Few Rejected Strings</span>
                      
                    </div>
                    {result.rejected.length === 0
                      ? <p className="rt-empty">All samples matched</p>
                      : (
                        <ul className="rt-string-list">
                          {result.rejected.map((s, i) => (
                            <li key={i} className="rt-string-item rt-string-item--rejected"
                              style={{ "--delay": `${i * 60}ms` }}>
                              <span className="rt-string-cross">✗</span>
                              <code className="rt-string-val">"{s}"</code>
                            </li>
                          ))}
                        </ul>
                      )
                    }
                  </section>
                </div>
              </>
            )}
          </div>
        )}

        {/* ── TEAM FOOTER ── */}
        <div className="rt-team-footer">
          <div className="rt-team-footer__inner">
            <div className="rt-team-footer__branding">
              <span className="rt-team-footer__icon">⬡</span>
              <span className="rt-team-footer__name">Team Leviathan</span>
            </div>
            <ul className="rt-team-footer__members">
              {TEAM_MEMBERS.map((m, i) => (
                <li key={i} className="rt-team-footer__member" style={{ "--mi": i }}>
                  <span className="rt-team-footer__member-name">{m.name}</span>
                  <span className="rt-team-footer__member-reg">{m.reg}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <footer className="rt-footer">
          <span>Regular Language Interpreter</span>
          <span className="rt-footer__dot">·</span>
          <span>Theory of Computation</span>
        </footer>

      </main>
    </div>
  );
}
