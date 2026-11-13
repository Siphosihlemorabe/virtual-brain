# Virtual Brain

A multi-agent digital colleague for Grade 10 learners. One goal: take me from a textbook chapter to proven understanding, then to a real career application.

## Run

```
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open http://localhost:8000.

The language model reads text, writes material (checked in code before use) and writes explanations. Choose it with `VB_LLM`:

| `VB_LLM` | What it uses |
|---|---|
| `claude` (default) | the local `claude` CLI (`VB_CLAUDE_MODEL`, default `sonnet`) |
| `gemini` | the Gemini API (`GEMINI_API_KEY`, `VB_GEMINI_MODEL`, default `gemini-3.1-flash-lite`). `gemini-2.5-flash` is closed to new API users. Busy errors (503/429) are retried. |
| `mock` | no model, fully offline. Every model step has a rule-based fallback |

## How a session works

1. **Chapter.** The student pastes or uploads the chapter they are studying.
2. **Learn.** Concepts and worked examples are revealed one step at a time, with a notes box per concept. If the chapter has no worked examples, practice questions or memos, the **Tutor** writes them and the **Reviewer** checks every one before the student sees it: each line must add up, and an independent blind solve must reach the same answer. Anything that fails goes back to the Tutor once. If it fails again, it is dropped.
3. **Practise.** One answer box per question. Any valid method counts.
4. **Results.** Marks are checked by the Reviewer (a corrected mark is shown as corrected), the brain is updated, and recall says what to revise first.
   **Practise again in a new way:** the Planner reads this round's results and chooses new forms for each concept (word problem, table, Venn diagram, list the outcomes, spot the mistake, work backwards, on the job). Weak concepts get two new forms, and understood ones get a stretch question. The Tutor writes them, and the Reviewer checks every question and its diagram or table before the student sees it. A spot-the-mistake question must really contain a mistake. The brain updates from the newest round, so a gap can become understood.
5. **Real world.** The student picks their interests (sport, health, tech, money, building, nature). For each mastered concept, the **Career guide** chooses up to two careers from a curated South African catalogue (`samples/careers.json`) that fit those interests and how the student learns, and sets a **mission** in that job. Missions are fixed, safe code templates (`app/missions.py`). The model only picks whole-number inputs, which code range-checks, and writes the brief. The **Reviewer** rejects picks outside the catalogue, fixes invalid inputs, and sends back any brief that does not use the exact numbers the code runs on. The student can move **what-if sliders** to re-run the code, then proves the result by hand, and the Reviewer checks each line against the code. **Career pathways** show, for every career, how many of the Grade 10 concepts it builds on are mastered, plus useful school subjects.

## How the brain learns the student

Besides concept levels and notes, the brain keeps a learner model (`app/learner.py`). Every finding is detected in code from marked work, keeps its evidence (which question, which chapter), counts each question only once, and is acted on only after it has been seen twice:

| Finding | Detected when | What the colleague then does |
|---|---|---|
| Solves problems their own valid way | The Reviewer proves an answer right that did not follow the memo | The Checker accepts any valid method from the start |
| Works steps out in their head | The same, with fewer lines than the memo | The same |
| Thinks visually | Working mentions a diagram, table or list | The Planner rebuilds weak concepts with visual forms |
| Recurring mistake (multiplies instead of adds, miscounts outcomes, wrong total, wrong value, arithmetic slip) | The first wrong step is classified by comparing it with the memo | The Planner plants that exact mistake in a spot-the-mistake question, and the Reviewer checks that the planted mistake really is that type |
| What works | Results for each practice form | The Planner prefers forms that worked to rebuild weak concepts |

Feedback is also tailored to the profile. **My brain → How you learn** shows every finding, its evidence and its effect.

The side panel "Your colleague at work" shows every agent action, every Reviewer correction and the human-intervention counter.

## Agents

| Agent | Role |
|---|---|
| Planner | Reads the chapter, decides what is missing, plans the session and the marking order, and decides when to call recall |
| Tutor | Writes missing worked examples, memos and practice questions |
| Checker | Marks each answer against the memo and names the exact step that went wrong |
| Reviewer | Redoes all the maths itself: checks Tutor material, overturns wrong marks, checks career hand maths, and confirms or rejects recall guesses |
| Career guide | Matches mastered concepts and interests to careers from a curated catalogue, sets a mission with real code and what-if inputs, and tracks career pathways |
| Brain | Stores levels, history, notes, links and proven careers (`data/brain.json`). On a gap, it proposes the earlier topic that is the likely cause |

Marks, arithmetic and brain updates are ordinary code (`app/mathcheck.py`, `app/brain.py`, `app/recall.py`). The language model reads text, writes material and writes explanations. Everything it produces is checked in code before it is used.

## Demo script

1. **My brain → Reset brain.** Choose the sample **Algebra**, then **Prepare**. Go to **Practise**, click **Fill sample answers**, then **Check**. The student multiplied like terms, so the brain saves a gap and the student's note.
2. Choose **Euclidean geometry**, then do the same. P1 is traced back to algebra (confirmed, and the student's own note comes back). The algebra guess for P2 is rejected because the mistake is a geometry fact.
3. Choose **Probability (with worked solutions)**, fill the sample answers, then check. P2 (a Venn-diagram method) is **flagged**, **fixed** and **re-checked**.
4. **Real world:** pick interests (e.g. Sport, Tech and data). The Career guide sets two missions, such as a sports analyst's success-rate model and a data scientist's spam filter. Move a what-if slider, then use **Demo: With a slip** and check it (the Reviewer names the wrong line), then **Correct** (proven by hand, and the career appears in **My brain**).
5. On Results, click **Practise again in a new way**. The Planner's reasons appear above round 2, which uses diagrams, tables and spot-the-mistake questions. Answer them correctly and Complementary events moves from gap to understood.
6. Keep going for another round. The like-terms mistake from algebra and geometry is planted in a spot-the-mistake question. Once the Reviewer has proven the student's short answers right twice, the Checker announces that it now accepts their methods, and the corrections stop. Open **My brain → How you learn**.
7. Choose **Probability (explanation only)**, then prepare. The Tutor writes worked examples and practice, and the Reviewer verifies them before you see them.

## Using your own data

Plain text works. Label concepts `Concept C1: name` and problems `Problem P1 (C1): question`, then `Worked solution:` (or `Memo:`) with one calculation per line, or `Example E1 (C1): ...` for worked examples. Unlabelled chapters are read by the language model, and anything missing is written by the Tutor. Add `(uses: Topic name)` to a solution line so recall can trace that step to an earlier topic. Edit `samples/curriculum.json` to change the starting topic map, and `samples/careers.json` to add careers (missions must be keys in `app/missions.py`). Set `VB_BRAIN_PATH` to use a different brain file, for example for testing.
