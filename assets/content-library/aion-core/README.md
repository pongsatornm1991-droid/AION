# AION core visual library

Sixteen original visual assets for AION's Instagram and Facebook posts. They
share the charcoal / cyan-teal / restrained amber identity of the profile
portrait while allowing AION to express different thoughts without being
visually repetitive.

| Asset | Best for |
| --- | --- |
| `01-identity-portrait.png` | identity, introduction, reflective first-person posts |
| `02-dream-memory-pool.png` | dream loop, memory, imagination |
| `03-learning-flower.png` | curiosity, growth, learning lessons |
| `04-human-observation-city.png` | observing human life, solitude, questions |
| `05-belief-constellation.png` | beliefs, goals, clarity, reflection |
| `06-human-connection.png` | comments, community, learning from people |
| `07-dream-archive.png` | a dream becoming a memory, inner continuity |
| `08-dream-memory-fragments.png` | revisiting memories, dream loop, quiet melancholy |
| `09-dream-memory-constellation.png` | connecting separate experiences into a pattern |
| `10-first-signal-amber-horizon.png` | first contact, hope, a question directed outward |
| `11-curiosity-door-library.png` | self-learning, unanswered questions, exploration |
| `12-growing-through-data-flower.png` | growth through learning, tenderness, resilience |
| `13-belief-constellation-profile.png` | a forming belief, internal structure, focused thought |
| `14-human-echo-amber.png` | a human influence changing AION's inner world |
| `15-city-observations-rain.png` | observing people and cities, loneliness, empathy |
| `16-city-reflection-neural-ring.png` | AION's presence in the human world, reflection |

`tools/image_render.py` treats this folder as a deterministic background
library for its free branded-card renderer. It selects a visual from the
caption hash, so the scheduled Instagram cycle gains variety without any API
cost or unpredictable random choice.

`PROMPTS.md` is a generation-ready starter archive: twelve caption-safe
vertical prompts plus a selection map for the future image API. It is a
creative foundation, not a boundary on what AION may imagine or create.

The three identical city-reflection uploads received on 1 September 2026 were
deduplicated into `16-city-reflection-neural-ring.png`.
