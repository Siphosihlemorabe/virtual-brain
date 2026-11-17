# Virtual Brain: research for the rebuild

Date: 17 November 2026. Status: research, nothing built yet.

**Goal.** Turn the Brain from a gimmick into a learner model that is actually useful and grounded in learning
science. Target user: an adult learning from online classes (Zoom) or course platforms (Udemy and similar),
through a browser plugin. First real test: my own AWS course.

---

## 1. The problem we are solving (and why it is real)

Video learning creates a specific, well-documented failure: **people feel they learned more than they did.**

- Fluent, well-produced lectures raise learners' *confidence* without raising actual learning: the
  "illusion of learning" from instructor fluency (Carpenter et al., *Metacognition and Learning*, 2018).
- Ease of processing is mistaken for mastery. Watching something many times raises confidence, not ability.
- Learners mind-wander during online lectures; short tests between segments **halved mind-wandering,
  tripled note-taking and improved retention** (Szpunar, Khan & Schacter, *PNAS*, 2013).

So the learner's problem is not "I need more content" (Udemy has plenty). It is: **"I don't know what I actually
know, and I'll forget most of it anyway."** That is exactly what a learner model can fix, and what quiz
generators alone do not.

## 2. What the science says works (and what doesn't)

From the most-cited review of study techniques (Dunlosky et al., *Psychological Science in the Public Interest*,
2013), which rated ten techniques:

| Utility | Technique | What it means for us |
|---|---|---|
| **High** | Practice testing (retrieval) | The core activity. Every update to the Brain should come from the learner *retrieving*, not watching. |
| **High** | Distributed practice (spacing) | Reviews scheduled over days, not crammed. Needs a memory model (section 3). |
| Moderate | Elaborative interrogation, self-explanation | "Why is this true?" / "Explain it in your words" prompts. |
| Moderate | Interleaved practice | Mix topics in reviews, especially ones the learner confuses. |
| **Low** | Rereading, highlighting, summarising | Rewatching and AI summaries feel productive but are low-value. **Don't build the product around summaries.** |

Three more effects that fit video learning directly:

- **Pretesting.** Questions asked *before* a segment, even when answered wrongly, improve learning of what follows,
  including from instructional videos (Carpenter & Toftness, 2017), and reduce mind-wandering in online lectures.
- **Interpolated testing.** Short quizzes *between* lecture segments (Szpunar et al., 2013, above).
- **Hypercorrection.** Errors made with **high confidence** are the *most* likely to be fixed after feedback, and the
  effect lasts at least a week (Butterfield & Metcalfe, 2001; persistence study in *Psychonomic Bulletin & Review*).
  → Ask for confidence before revealing an answer, and treat confident errors as the most valuable moments.

## 3. What the Brain should actually model

A learner model is only useful if every number in it comes from evidence and changes what happens next. Each
idea below is an established model, not something we invent.

### 3.1 Two different things per concept: *learned* vs *will remember*

| Quantity | Meaning | Model to use | Why this one |
|---|---|---|---|
| **Mastery** | Has the learner got this concept yet? | Bayesian Knowledge Tracing (BKT) style update per concept | Interpretable. Extended BKT performs on par with deep models on many datasets, and deep models are hard to explain (Khajah, Lindsey & Mozer, 2016; Gervet et al.). We must be able to say *why* the Brain thinks something. |
| **Memory strength** | Will they recall it today? | FSRS (Difficulty, Stability, Retrievability) | Open-source, used by Anki, reported to need 20–30% fewer reviews than the older SM-2 for the same retention. Retrievability **falls daily**, so the Brain visibly forgets, which drives spaced reviews. |

### 3.2 Calibration: does the learner know what they know?

- Before each answer: "How sure are you?" (3 levels is enough).
- Track the **calibration gap** per concept: confidence minus accuracy.
- Overconfident concepts are flagged and prioritised; confident errors get rich feedback (hypercorrection).
- This targets the video "illusion of learning" in section 1. **Most quiz tools don't do this. It is our strongest
  differentiator.**

### 3.3 How topics connect: a prerequisite map

- Knowledge Space Theory (Doignon & Falmagne, 1985; used by ALEKS): concepts form a prerequisite graph.
- The **outer fringe** is what the learner is *ready to learn next*. ALEKS reports that learners succeed about
  93% of the time on items picked from the outer fringe.
- For us: the Planner builds the graph from the transcript (the model proposes), and edges are checked (code and
  Reviewer verify). Recommendations come from the fringe, not a fixed order.
- We already have a version of this: `builds_on` and `recall.py` (guess the root cause, Reviewer confirms).

### 3.4 Confusions and misconceptions

- Record **which concepts the learner mixes up** (for AWS: S3 vs EBS vs EFS, security groups vs NACLs).
- Confused pairs get **interleaved discrimination questions** ("which one fits this case, and why not the other?").
- This generalises today's maths-only mistake classifier in `learner.py`.

### 3.5 What we keep from the current Brain

- Only checked evidence updates the Brain (the Reviewer gate).
- A pattern only drives behaviour after it has been seen at least twice (`CONFIRM = 2`).
- Every entry keeps its evidence and its effect on behaviour (`learner.view`).

## 4. The loop, per lecture segment

1. **Before:** 1–2 pretest questions (pretesting effect).
2. **Watch** the segment.
3. **After:** 2–3 retrieval questions, with confidence asked first (interpolated testing, calibration).
4. **Feedback** with a link to the exact moment in the video (timestamp), so rewatching is targeted, not rereading.
5. **Brain update:** mastery (BKT), memory (FSRS), calibration, confusions.
6. **Later:** spaced, interleaved reviews scheduled by FSRS, prioritising overconfident and confused concepts.

## 5. Self-correction for transcript-based questions

Our hackathon strength carries over. Questions generated from transcripts are mostly good, but not always:

- Recent studies find LLM-generated multiple-choice questions mostly meet item-writing standards, with relevance
  around 89–94% and answerability around 94–97%. That is good, but it means **about 1 in 20 questions can be
  unanswerable or off-topic.** Transcripts beat video frames as the source context.
- **Reviewer rules (in code wherever possible):**
  - Every question must cite the transcript span (with timestamp) that supports its answer. No span, no question.
  - A blind solve: the Reviewer answers from the cited span only. It must match the Tutor's key.
  - Distractors must not also be supported by the transcript.
  - Failed items go back to the Tutor once, then are dropped (same as today).

## 6. The 3D brain: make it a real view of the model, not decoration

The risk is real: **decorative graphics can hurt learning.** Meta-analyses of the "seductive details" effect find
learning drops when appealing but irrelevant material is added (g ≈ −0.33), and Mayer's coherence principle says to
leave extraneous material out. Graphics can raise *liking* without raising learning (Sung & Mayer, 2012).

The counter-evidence is just as relevant: **open learner models** (showing learners their own model) help
metacognition. A 2020 systematic review found positive effects on self-regulated learning, and learners who could see
their model chose what to work on better.

**Design rule:** every visual property of the brain must encode a number from section 3, and one click must lead to
an action.

| Visual | Encodes |
|---|---|
| Region / cluster | A subject → topic (e.g. AWS → Storage → S3) |
| Size | How much of the course covers it |
| Colour | Mastery (BKT) |
| Brightness / glow | Retrievability *today* (FSRS). It visibly dims as the learner forgets |
| Pulse | Due for review now |
| Warning outline | Overconfident (calibration gap) |
| Links between regions | Prerequisites, and confused pairs |
| Click | The topic's evidence and a "review now" button |

Always pair the 3D view with a plain list ("3 topics due, 1 overconfident"). The list does the work; the brain makes
the model visible and motivating. **This is a hypothesis to test with real learners, not a proven benefit.**

## 7. Getting the transcript

**Goal: work on every platform** (Zoom, Udemy, Coursera, DataCamp, …). Priority: Udemy, then Coursera; first test
on DataCamp (my AWS course).

### 7.1 What the platforms' terms say

| Platform | Captions in the player? | Terms on extracting them |
|---|---|---|
| **Udemy** | Yes | Could not read the terms (site blocked the request). Existing caption extensions warn they *may conflict* with Udemy's Terms. **Unverified: read before building.** |
| **Coursera** | Yes; some courses offer a subtitle download | Acceptable Use Policy prohibits "content, data, or text scraping … through manual, mechanical, or automated means including by the use of bots or other similar software". **Reading captions from the page is out.** |
| **DataCamp** | Yes, in 17 languages; not downloadable | DataCamp's *Recruit* terms prohibit "any automated means or form of scraping or data extraction to … download, query or otherwise collect information". The main learning terms were not checked; **assume the same until verified.** |

### 7.2 Recommended capture: one method that works everywhere

**Tab audio, transcribed on the learner's side.** The plugin records only the audio already playing in the learner's
own tab and transcribes it. It never reads the platform's pages, captions or data, and it works the same on Zoom,
Udemy, Coursera, DataCamp and YouTube.

- **Capture:** Chrome MV3 `tabCapture.getMediaStreamId` plus an offscreen document (Chrome 116+), started by a click.
- **Transcription, preferred:** a local Whisper model (e.g. faster-whisper) on the learner's machine. Free, and the
  audio never leaves the device, which helps with POPIA and with course copyright.
- **Transcription, cloud option:** Amazon Transcribe **batch** in eu-north-1 (no streaming in that Region).
  **Checked: Transcribe is on the Paid plan list only, and the project is on the free plan**, so it is unavailable
  until the project upgrades. A faster-whisper worker in our own container works on either plan.
- **Store the transcript only, never the audio.** Keep it private to the learner's own Brain; never share or
  redistribute it.
- **Also offer manual import** (paste or upload a transcript the learner is allowed to use, e.g. their own notes or
  a host-provided Zoom VTT).

**Still a legal question, not settled:** recording course audio for personal study may still fall under a
platform's copying clauses. For my own testing on my own account the risk is low. **Before launching as a product,
get a legal opinion or a platform partnership.**

### 7.3 All capture routes compared

| Source | Best route | Notes |
|---|---|---|
| **Course platforms** (Udemy, others) | Read the captions the player already loads (the browser TextTrack API) | Cheapest, instant, no audio processing. Several existing extensions do this. Those extensions warn that it **may conflict with Udemy's Terms of Service**. I could not fetch Udemy's terms (the site blocked the request), so **read them before building**. Safest: personal study use only, nothing redistributed or stored beyond the learner's own Brain. |
| **Zoom, as host** | Zoom Cloud Recording API: `recording.transcript_completed` webhook, VTT file | Needs the host's account and cloud recording. |
| **Zoom, as participant** | Ask the host for the transcript; else capture tab audio after consent | Chrome MV3: `tabCapture.getMediaStreamId` plus an offscreen document (Chrome 116+). |
| **No captions at all** | Tab audio → transcription after the session | **Amazon Transcribe in eu-north-1 is batch only; streaming is not offered there** (checked on AWS's endpoints page). Our project can't use other Regions, so live captions via AWS are out. Batch after each segment works. A local Whisper model is the alternative. |

**Consent (South Africa):** RICA allows a party to a conversation to record it (one-party consent), but POPIA
governs storing and processing others' personal information in that recording. Plan: a clear in-app consent prompt,
transcript only (no audio kept), and a strong preference for host-provided transcripts. This is not legal advice.

**Plan check (done 17 Nov):** the project is on the **free plan**. Amazon Transcribe is Paid-plan only. Amazon
Bedrock is on the free plan, but **no Claude model is available in-Region in eu-north-1** (only cross-Region
routing, which projects don't support), so the language model must come from the Anthropic API directly. See
`docs/design/architecture.md`.

## 8. What already exists in the market

- **Coursera Coach** answers questions and quizzes from lecture transcripts, but only inside Coursera.
- **NotebookLM** makes quizzes and flashcards from sources, but is not a true spaced-repetition system: it doesn't
  plan reviews weeks ahead.

**Our gap:** works across platforms (plugin); a persistent learner model with memory decay, calibration and
prerequisites; and self-checked questions tied to timestamps. Nobody above models *how sure* the learner is versus
*how right* they are.

## 9. Proposed first slice (for my AWS course)

1. Extension captures tab audio from one DataCamp lecture → local Whisper transcript → segments by topic →
   sends to the backend.
2. Planner builds topics and a prerequisite map; Tutor writes pretest and retrieval questions with cited spans;
   Reviewer verifies.
3. Learner answers with confidence → Brain updates mastery, memory (FSRS), calibration.
4. Brain view: three.js brain with the encodings in section 6, plus the plain due-list.
5. Next day: spaced review of yesterday's topics. **Success check:** does next-day recall beat my usual
   rewatching?

## 10. Open questions

- ~~Which platform is the AWS course on?~~ DataCamp. Target all platforms; Udemy, then Coursera, as priorities.
- Legal check on recording course audio for personal study, before any public release.
- Do we keep a maths path, or move fully to the online-course audience?
- How do we evaluate it? Proposed: compare next-day and one-week recall on reviewed vs unreviewed topics in my own
  course, then a small pilot.

---

## Sources

- Dunlosky et al. (2013), *Improving Students' Learning With Effective Learning Techniques*: https://pubmed.ncbi.nlm.nih.gov/26173288/
- Szpunar, Khan & Schacter (2013), *Interpolated memory tests reduce mind wandering…*, PNAS: https://www.pnas.org/doi/pdf/10.1073/pnas.1221764110
- Carpenter et al. (2018), instructor fluency and the illusion of learning: https://eric.ed.gov/?id=EJ1172606
- Overcoming overconfidence in video lectures (interpolated testing): https://www.researchgate.net/publication/260482172
- Pretesting and online lectures: https://www.researchgate.net/publication/347120870 ; review: https://www.researchgate.net/publication/374157738
- Hypercorrection effect: https://en.wikipedia.org/wiki/Hypercorrection_(psychology) ; persistence over a week: https://link.springer.com/article/10.3758/s13423-011-0173-y
- FSRS algorithm: https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm ; https://github.com/open-spaced-repetition/fsrs-rs
- BKT vs DKT: Khajah, Lindsey & Mozer (2016) https://arxiv.org/abs/1604.02416 ; Gervet et al. https://files.eric.ed.gov/fulltext/EJ1273917.pdf
- Knowledge Space Theory and ALEKS: https://jmatayoshi.github.io/publications/JMP2021_KST_ALEKS_preprint.pdf
- Open learner models and self-regulated learning (systematic review, 2020): https://www.sciencedirect.com/science/article/abs/pii/S0360131520300774 ; Bull & Kay: https://www.semanticscholar.org/paper/Open-Learner-Models-Bull-Kay/a52671044b34a73d896d3ecceaeca443b19508da
- Seductive details meta-analysis: https://www.researchgate.net/publication/257690772 ; Sung & Mayer (2012): https://www.sciencedirect.com/science/article/abs/pii/S0747563212000921
- LLM-generated MCQs from transcripts: https://public.websites.umich.edu/~kevynct/pubs/L_S_2024_WorkInProgress_Question_Generation_CRFinal2.pdf ; https://link.springer.com/article/10.1007/s11423-026-10646-7
- Amazon Transcribe endpoints (batch vs streaming by Region): https://docs.aws.amazon.com/general/latest/gr/transcribe.html
- Services on the free and paid plans of the new AWS experience: https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html
- Bedrock model availability by Region (in-Region vs cross-Region): https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html
- Chrome MV3 tab audio capture: https://github.com/GoogleChrome/developer.chrome.com/blob/main/site/en/docs/extensions/mv3/screen_capture/index.md
- Zoom transcripts via API: https://www.recall.ai/blog/7-apis-to-get-zoom-transcripts-a-comprehensive-guide
- Udemy transcript extensions and ToS warnings: https://github.com/pras-ops/udemy-transcript-extractor
- Coursera Terms of Use (Acceptable Use Policy): https://www.coursera.org/about/terms
- DataCamp terms on automated access: https://www.datacamp.com/terms-of-use-recruit-jobs ; subtitles: https://support.datacamp.com/hc/en-us/articles/360007678574-Are-DataCamp-s-video-subtitles-available-in-multiple-languages
- South Africa recording laws (RICA, POPIA): https://www.recordinglaw.com/south-africa/recording-laws/
- NotebookLM and Coursera Coach: https://notebooklm-guide.com/notebooklm-quiz-flashcard-upgrade-2026-enhanced/ ; https://agent-finder.co/reviews/coursera-coach
