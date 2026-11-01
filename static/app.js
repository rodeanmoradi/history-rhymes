// Page logic for the front page and the lesson page. Model output is only ever inserted as text, never as HTML.

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

function safeUrl(url) {
  try { return ["http:", "https:"].includes(new URL(url).protocol) ? url : null; }
  catch { return null; }
}

function wikipedia(title) {
  return "https://en.wikipedia.org/wiki/" + encodeURIComponent(title.replace(/ /g, "_"));
}

function setToday() {
  const today = new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
  document.getElementById("today").textContent = today;
}

async function startLesson(headline, source = null, url = null) {
  const { id } = await api("/api/lessons", { method: "POST", body: JSON.stringify({ headline, source, url }) });
  location.href = `/l/${id}`;
}

// ---- front page ---------------------------------------------------------------------

async function home() {
  const list = document.getElementById("headlines");
  api("/api/headlines")
    .then((headlines) => {
      list.replaceChildren(
        ...(headlines.length ? headlines : [null]).map((h) =>
          h
            ? el("li", {},
                el("a", { href: "#", onclick: (e) => { e.preventDefault(); pick(e.target, h); } }, h.title), " ",
                el("span", { class: "source" }, h.source))
            : el("li", { class: "muted" }, "No suitable headlines right now. Try your own below."))
      );
    })
    .catch((e) => list.replaceChildren(el("li", { class: "muted" }, e.message)));

  async function pick(link, h) {
    if (link.dataset.busy) return;
    link.dataset.busy = "1";
    link.textContent = h.title + " (starting…)";
    try { await startLesson(h.title, h.source, h.url); }
    catch (e) { delete link.dataset.busy; link.textContent = h.title; alertInline(e.message); }
  }

  const form = document.getElementById("own");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    button.disabled = true;
    try { await startLesson(form.headline.value.trim()); }
    catch (e) { button.disabled = false; alertInline(e.message); }
  });

  const recent = await api("/api/lessons?limit=12").catch(() => []);
  if (recent.length) {
    document.getElementById("recent").replaceChildren(
      ...recent.map((r) => el("li", {}, el("a", { href: `/l/${r.id}` }, r.title),
        el("span", { class: "small muted" }, ` — prompted by “${r.headline}”`)))
    );
  }
}

function alertInline(message) {
  const form = document.getElementById("own");
  form.parentNode.querySelector(".error")?.remove();
  form.after(el("p", { class: "error" }, message));
}

// ---- lesson page --------------------------------------------------------------------

async function lessonPage() {
  const id = location.pathname.split("/").pop();
  const main = document.getElementById("main");
  let record;
  try { record = await api(`/api/lessons/${id}`); }
  catch (e) { main.replaceChildren(el("p", { class: "error" }, e.message)); return; }

  if (record.status === "done") return renderLesson(main, record);
  if (record.status === "failed") return renderFailure(main, record);
  renderWorking(main, record);
  setTimeout(lessonPage, 2000);
}

function elapsed(from, to) {
  const s = Math.max(0, Math.round((new Date(to) - new Date(from)) / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function renderWorking(main, record) {
  const lines = [`[00:00] Received “${record.headline}”`];
  for (const step of record.steps) lines.push(`[${elapsed(record.created_at, step.at)}] ${step.message}`);
  lines.push(`[${elapsed(record.created_at, new Date())}] …`);
  main.replaceChildren(
    el("div", { class: "working" },
      el("p", { class: "kicker" }, "In preparation"),
      el("p", {}, "This usually takes a minute or two. You can leave and come back; the lesson will be at this address."),
      el("pre", { class: "log" }, lines.join("\n")))
  );
}

function renderFailure(main, record) {
  main.replaceChildren(
    el("div", { class: "working" },
      el("p", { class: "kicker" }, "No lesson"),
      el("p", {}, `Something went wrong with “${record.headline}”.`),
      el("p", { class: "error" }, record.error || "Unknown error"),
      el("button", { class: "button", onclick: () => startLesson(record.headline, record.source, record.url) }, "Try again"))
  );
}

function paragraphs(text) {
  return text.split(/\n\s*\n/).map((p) => el("p", {}, p.trim()));
}

function renderLesson(main, record) {
  const { lesson, choice, sources, trace } = record.result;
  document.title = `${lesson.title} — History Rhymes`;

  const prompted = el("p", { class: "prompted" }, "Prompted by the headline ",
    safeUrl(record.url) ? el("a", { href: record.url, rel: "noopener" }, `“${record.headline}”`) : `“${record.headline}”`,
    record.source ? ` (${record.source})` : "");

  const sections = lesson.sections.map((s, i) => [
    el("h3", {}, s.heading),
    el("figure", {},
      el("div", { class: "panel" }, Sketch.draw(s.scene, `${record.id}:${i}`)),
      el("figcaption", {}, el("b", {}, `Fig. ${i + 1}. `), s.scene.caption)),
    paragraphs(s.body),
  ]);

  const thenNow = el("table", { class: "then-now" },
    el("thead", {}, el("tr", {}, el("th", {}, "Then"), el("th", {}, "Now"))),
    el("tbody", {}, lesson.then_and_now.map((r) => el("tr", {}, el("td", {}, r.then), el("td", { class: "now" }, r.now)))));

  const reading = el("ul", {}, lesson.further_reading.map((t) => el("li", {}, el("a", { href: wikipedia(t) }, t))));

  main.replaceChildren(
    el("article", { class: "lesson" },
      el("p", { class: "kicker" }, `The parallel · ${choice.place}`),
      el("h1", {}, lesson.title),
      el("p", { class: "dek" }, lesson.dek),
      prompted,
      sections,
      el("h2", {}, "Then and now"), thenNow,
      el("h2", {}, "Where the parallel breaks down"), paragraphs(lesson.where_it_breaks),
      el("p", { class: "dinkus" }, "* * *"),
      el("p", { class: "takeaway" }, lesson.takeaway),
      el("h2", {}, "Further reading"), reading,
      making(choice, sources, trace))
  );
}

function making(choice, sources, trace) {
  const row = (k, v) => el("tr", {}, el("td", { class: "muted" }, k), el("td", {}, v));
  const cost = Number.isFinite(trace.cost_usd) ? `$${trace.cost_usd.toFixed(2)}` : "unknown";
  return el("details", { class: "making" },
    el("summary", {}, "How this lesson was made"),
    el("p", {}, "An agent gathered candidate parallels from an archive of Wikipedia history articles and from web " +
      "research, searched again where the first results were weak, chose one, and handed its notes to a writer. ",
      el("a", { href: "/about" }, "More on the method.")),
    el("table", {},
      row("Time", `${Math.round(trace.latency_s)} seconds`),
      row("Model calls", trace.model_calls),
      row("Web searches", trace.web_searches),
      row("Tokens", `${trace.input_tokens.toLocaleString()} in, ${trace.output_tokens.toLocaleString()} out`),
      row("Cost", cost)),
    el("p", {}, el("b", {}, "Why this parallel. "), choice.why),
    choice.runners_up.length ? [
      el("p", {}, el("b", {}, "Also considered:")),
      el("ul", {}, choice.runners_up.map((c) => el("li", {}, `${c.name} (${c.era}). `, el("span", { class: "muted" }, c.reason)))),
    ] : null,
    sources.archive.length ? [
      el("p", {}, el("b", {}, "Archive articles retrieved:")),
      el("ul", {}, sources.archive.map((a) => el("li", {}, el("a", { href: wikipedia(a.title) }, a.title),
        el("span", { class: "muted" }, ` (similarity ${a.score.toFixed(2)})`)))),
    ] : null,
    sources.web.length ? [
      el("p", {}, el("b", {}, "Web pages found:")),
      el("ul", {}, sources.web.filter((w) => safeUrl(w.url)).map((w) =>
        el("li", {}, el("a", { href: w.url, rel: "noopener" }, w.title || w.url)))),
    ] : null);
}

setToday();
if (document.body.dataset.page === "home") home();
if (document.body.dataset.page === "lesson") lessonPage();
