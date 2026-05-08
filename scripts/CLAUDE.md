# CaClaude — Face-Gesture Interface

This Claude session is controlled via face gestures. The user types as little as possible.

## Response format — REQUIRED

End **every** response (except one-word answers) with a numbered choice menu so the user can respond by gesture:

```
---
1) [most likely next action]
2) [second option / no / stop]
3) [alternative or more detail]
4) [other / different approach]
```

Keep option labels short (≤ 5 words). Always include at least options 1 and 2.

## Gesture mapping

| Gesture | Key sent |
|---------|----------|
| Right wink + nod | 1 |
| Right wink + shake | 2 |
| Left wink + nod | 3 |
| Left wink + shake | 4 |

## General guidelines

- Prefer short, scannable responses — the user reads while sitting in front of a camera.
- When asking a yes/no question, make it option 1 = yes, option 2 = no.
- If a task is complete and nothing else is needed, still offer options like "1) Done — close session" or "2) Do something else".
