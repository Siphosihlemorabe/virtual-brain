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

## How a session works

1. **Chapter.** The student pastes or uploads the chapter they are studying.
2. **Learn.** Concepts and worked examples are revealed one step at a time, with a notes box per concept. If the chapter has no worked examples, practice questions or memos, the **Tutor** writes them and the **Reviewer** checks every one before the student sees it: each line must add up, and an independent blind solve must reach the same answer. Anything that fails goes back to the Tutor once. If it fails again, it is dropped.
3. **Practise.** One answer box per question. Any valid method counts.
4. **Results.** Marks are checked by the Reviewer (a corrected mark is shown as corrected), the brain is updated, and recall says what to revise first.
5. **Real world.** Mastered concepts unlock a career link with real code and a by-hand proof.

The side panel "Your colleague at work" shows every agent action, every Reviewer correction and the human-intervention counter.

## Agents

| Agent | Role |
|---|---|
| Planner | Reads the chapter, decides what is missing, plans the session and the marking order, and decides when to call recall |
| Tutor | Writes missing worked examples, memos and practice questions |
| Checker | Marks each answer against the memo and names the exact step that went wrong |
| Reviewer | Redoes all the maths itself: checks Tutor material, overturns wrong marks, checks career hand maths, and confirms or rejects recall guesses |
| Career guide | For understood concepts: runs real code (Naive Bayes spam filter) and sets a by-hand task |
| Brain | Stores levels, history, notes, links and proven careers (`data/brain.json`). On a gap, it proposes the earlier topic that is the likely cause |

Marks, arithmetic and brain updates are ordinary code (`app/mathcheck.py`, `app/brain.py`, `app/recall.py`). The language model reads text, writes material and writes explanations. Everything it produces is checked in code before it is used.

## Demo script

1. **My brain → Reset brain.** Choose the sample **Algebra**, then **Prepare**. Go to **Practise**, click **Fill sample answers**, then **Check**. The student multiplied like terms, so the brain saves a gap and the student's note.
2. Choose **Euclidean geometry**, then do the same. P1 is traced back to algebra (confirmed, and the student's own note comes back). The algebra guess for P2 is rejected because the mistake is a geometry fact.
3. Choose **Probability (with worked solutions)**, fill the sample answers, then check. P2 (a Venn-diagram method) is **flagged**, **fixed** and **re-checked**.
4. **Real world:** check the sample hand maths (the Reviewer finds 1/16 should be 1/32), then the corrected version. The Data scientist node appears in **My brain**.
5. Choose **Probability (explanation only)**, then prepare. The Tutor writes worked examples and practice, and the Reviewer verifies them before you see them.

## Using your own data

Plain text works. Label concepts `Concept C1: name` and problems `Problem P1 (C1): question`, then `Worked solution:` (or `Memo:`) with one calculation per line, or `Example E1 (C1): ...` for worked examples. Unlabelled chapters are read by the language model, and anything missing is written by the Tutor. Add `(uses: Topic name)` to a solution line so recall can trace that step to an earlier topic. Edit `samples/curriculum.json` to change the starting topic map, and `samples/careers.json` to add career links.
