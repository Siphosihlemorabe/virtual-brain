# Self-test protocol: does the Virtual Brain method actually help me remember?

Date: 17 November 2026. Owner: Siphosihle. Duration: about 8 days, roughly 2.5 hours in total.

**Question:** a week after studying an AWS Cloud Practitioner lecture, do I remember more when I study it the
Virtual Brain way (brain dump, teach-back, quiz with confidence) than when I study my usual way?

**Why before building:** if the method doesn't make a difference I can feel on myself, an app that automates it
won't either. This costs a week and no code.

---

## 1. Decide the pass mark now (before any results)

Fill this in and don't change it later:

| Result | My threshold | Meaning |
|---|---|---|
| Method A score minus usual-study (B) score, one week later | at least **15 percentage points** | The method is worth building |
| Method A minus multiple-choice-only (C) | at least **10 points** | Brain dump and teach-back add real value beyond a quiz |
| Would I do method A again without being asked? (§6) | **Yes** | People will actually use it |

If A beats B but not C, the quiz alone is the useful part. If A doesn't beat B, we rethink before stage 0.

## 2. Pick three lectures

- Three DataCamp AWS Cloud Practitioner videos **I haven't watched**, of similar length and difficulty,
  ideally from the same chapter. Write their titles below.
- **Assign the conditions randomly**: write A, B and C on three bits of paper and draw one per lecture. Picking by
  hand tends to give the favourite method the easiest lecture.

| Lecture title | Length | Condition (drawn) |
|---|---|---|
| | | |
| | | |
| | | |

## 3. The three conditions (same time for each: 15 minutes on day 0, 5 minutes on day 2)

**A. The Virtual Brain method** (done with Claude in a chat, by hand)
1. **Brain dump** (3 min): straight after the video, type everything I remember, without looking.
2. Claude compares it with the transcript and shows **what I missed, with the lecture's words** (2 min).
3. **Teach-back** (5 min): explain the two most important ideas as if teaching a friend. Claude tries to answer two
   exam-style questions using **only what I said**; where it can't, I see my gap.
4. **Quiz with confidence** (5 min): 4 questions; before each answer I say Guessing, Fairly sure or Sure.
5. **Day 2** (5 min): a new brain dump, then 3 quiz questions on what I missed or got wrong.

**B. My usual way**
- 15 minutes doing whatever I normally do: rewatch parts, reread notes, write notes. **No self-testing.**
- **Day 2** (5 min): the same, again.

**C. Multiple choice only**
- 15 minutes of multiple-choice questions with feedback (Claude writes them from the transcript), with confidence
  ratings.
- **Day 2** (5 min): new multiple-choice questions on the same lecture.

## 4. The transcript (needed for A, C and the final test)

We need the lecture's words without scraping DataCamp (research §7). Use one of these:

1. **Recommended:** record the video's audio on my own computer while I watch, for personal study, then
   transcribe it locally with faster-whisper. **This also tests open item 9 (transcription accuracy on my accent
   and AWS terms) for free.** I'd write a small throwaway script for this, outside the app, if you agree.
2. **Fallback:** my own detailed notes plus screenshots of the slides. Weaker, because the final test then depends
   on my notes.

## 5. The final test (written before I study, taken on day 7)

- On day 0, **before studying**, Claude writes the final test from each transcript and saves it in
  `docs/validation/final-test/` (or a sealed file). **I don't open it until day 7.**
- Per lecture: **6 short-answer recall questions plus 2 exam-style scenario questions**, written so they don't copy
  any question used while studying.
- Day 7: closed book, all three lectures in one sitting, in random order. Before each answer I note my
  confidence (Guessing / Fairly sure / Sure).
- **Marking:** each question has 1–3 key points, written with the test. Claude marks against them, quoting my
  answer; I can dispute any mark, and disputes are settled against the transcript.

## 6. What I record

| When | What |
|---|---|
| Before each video | 3 quick questions on the topic, to check I didn't already know it (same for all three lectures) |
| After each day-0 session | Effort (1–5), enjoyment (1–5), and "would I do this again unprompted?" (yes/no) |
| Day 7 | Score per lecture (%), confidence per answer, time taken |
| Throughout | Anything annoying or surprising, in one line each |

**Calibration check:** compare my confidence with my accuracy per condition. Does method A leave me better
calibrated?

## 7. Schedule

| Day | Do | Time |
|---|---|---|
| 0 | Set the pass mark; pick and assign lectures; record audio, transcribe; Claude writes the sealed final test | 40 min |
| 0 | Watch lecture 1 + its condition; lecture 2 + its condition; lecture 3 + its condition | about 75 min |
| 2 | The 5-minute day-2 session for each condition | 15 min |
| 7 | Final test, then score with Claude | 30 min |
| 8 | Write up: results against the pass mark, decision | 15 min |

## 8. Honest limits

- **One learner, three lectures.** This is a signal, not proof. A clear difference counts; a small one doesn't.
- **I know the hypothesis**, which can bias effort. Equal time per condition limits this.
- **Lectures differ in difficulty.** Random assignment and the pre-video check reduce, but don't remove, this.
- **Prior AWS knowledge** may raise all scores. The pre-video check shows how much.

## 9. Write-up template

```
Lectures and conditions:
Day 7 scores:   A __%   B __%   C __%
A − B: __ points (pass mark 15)     A − C: __ points (pass mark 10)
Calibration (confidence − accuracy):   A __   B __   C __
Would I do A again unprompted?  yes / no
What annoyed me:
Decision:  build as specced / move toward the exam coach / rethink
```
