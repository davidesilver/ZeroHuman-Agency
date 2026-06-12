# Reddit — r/selfhosted (mer 24/6) · r/SideProject (gio 25/6)

Regole comuni: post nativo in prima persona, storia prima del link, dichiarare che è il proprio progetto (richiesto dalle regole di r/selfhosted), link al repo in fondo, rispondere a tutti i commenti il giorno stesso.

## r/selfhosted — mercoledì 24 giugno

**Titolo:** ZeroHuman – self-hosted AI content pipeline with multi-agent review (MIT)

**Corpo:**

> I've been lurking here for years, so I'll keep it honest: this is my project.
>
> My content workflow was 10 tools and a spreadsheet — feed reader for research,
> ChatGPT tab for drafts, Buffer for scheduling, a sheet for "what worked".
> ZeroHuman collapses that into one self-hosted stack: it pulls from RSS/search/
> YouTube, scores items on dimensions you configure, drafts platform-native posts,
> and runs every draft through a four-agent review panel (critic, fact-checker,
> creative, synthesis) before it reaches me for approval. Social metrics flow back
> into the scoring weights, so over time it learns what works for my audience.
>
> Stack: Next.js + FastAPI + Supabase (self-hostable), MIT licensed.
> Default compose profile is 2 containers; video tooling and social publishing
> are opt-in profiles.
>
> **What's behind the `social` profile:** Postiz, which many of you already know —
> I didn't rebuild scheduling, I built everything that happens *before* scheduling
> (research, scoring, editorial review, the metrics feedback loop) and use Postiz
> as the publishing satellite.
>
> Nothing publishes without human approval. The name is about the busywork,
> not the judgment.
>
> Repo: https://github.com/davidesilver/ZeroHuman-Agency — happy to answer
> anything about the architecture or the multi-agent review.

## r/SideProject — giovedì 25 giugno

**Titolo:** I built an AI content team that learns from my social metrics — open source, self-hosted

**Corpo:** versione più breve e personale del post sopra: il problema (10 tool e uno spreadsheet), la soluzione in 3 righe, la GIF demo, cosa ho imparato costruendolo (multi-agent review cattura classi di errori diverse), link repo. Tono builder-to-builder, niente feature list completa.
