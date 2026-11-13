# Virtual Brain

A multi-agent digital colleague for Grade 10 learners. One goal: take me from a textbook chapter to proven understanding, then to a real career application.

## Run

```
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open http://localhost:8000.

The language model reads text and writes explanations only. Choose it with `VB_LLM`:

| `VB_LLM` | What it uses |
|---|---|
| `claude` (default) | the local `claude` CLI (`VB_CLAUDE_MODEL`, default `sonnet`) |
| `gemini` | the Gemini API (`GEMINI_API_KEY`, `VB_GEMINI_MODEL`, default `gemini-2.5-flash`) |
| `mock` | no model, fully offline. Every model step has a rule-based fallback |

## Agents

| Agent | Role |
|---|---|
| Planner | Reads the chapter into concepts and problems, uses the brain to plan the marking order, and decides when to call recall |
| Checker | Reads the student's working and marks each problem against the worked solution, naming the exact step |
| Reviewer | Redoes all the maths itself. Flags wrong marks and sends them back to the Checker, then re-checks. Also checks career hand maths and confirms or rejects recall guesses |
| Career guide | For understood concepts: runs real code (Naive Bayes spam filter) and sets a by-hand task |
| Brain | Stores levels, history, notes, links and proven careers (`data/brain.json`). On a gap, it proposes the earlier topic that is the likely cause |

Marks, arithmetic and brain updates are ordinary code (`app/mathcheck.py`, `app/brain.py`, `app/recall.py`). The model's reading is checked so it cannot change a number. If it does, the rule-based reader is used and the log says so.

## Demo script (about 4 minutes)

1. **Reset brain.** Load **Algebra (earlier topic)**, then Run. The student multiplied like terms. The brain saves a gap and the student's note.
2. Load **Euclidean geometry**, then Run. P1 is traced back to algebra: the Reviewer confirms it because step 2 uses algebra, and the student's own algebra note comes back. For P2, the Reviewer *rejects* the algebra guess because step 1 is a geometry fact.
3. Load **Probability: first attempt**, then Run. The Checker marks P2 (a valid Venn-diagram method) as partly. The Reviewer **flags** it, the Checker **fixes** it, and the Reviewer **re-checks** it. The Reviewer corrections counter goes up by 1.
4. Career link: **Load sample hand maths**, then **Check**. The Reviewer finds the wrong line (1/16 should be 1/32). Click **Load corrected**, then **Check**. The career is proven, and the brain map gains a Data scientist node.
5. Load **Probability: improved working**, then Run. Complementary events moves from gap to understood. Click the topic to show its history.

## Using your own data

Plain text works. Label concepts `Concept C1: name` and problems `Problem P1 (C1): question`, then `Worked solution:` with one calculation per line. Add `(uses: Topic name)` to a solution line so recall can trace that step to an earlier topic. In the student's working, start each problem with `P1:`. Edit `samples/curriculum.json` to change the starting topic map, and `samples/careers.json` to add career links.
