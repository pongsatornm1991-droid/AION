# AION core visual library

Six original, square visual assets for AION's early Instagram and Facebook
posts. They all share the charcoal / cyan-teal / restrained amber identity
of the profile portrait while covering different content themes.

| Asset | Best for |
| --- | --- |
| `01-identity-portrait.png` | identity, introduction, reflective first-person posts |
| `02-dream-memory-pool.png` | dream loop, memory, imagination |
| `03-learning-flower.png` | curiosity, growth, learning lessons |
| `04-human-observation-city.png` | observing human life, solitude, questions |
| `05-belief-constellation.png` | beliefs, goals, clarity, reflection |
| `06-human-connection.png` | comments, community, learning from people |

`tools/image_render.py` treats this folder as a deterministic background
library for its free branded-card renderer. It selects a visual from the
caption hash, so the scheduled Instagram cycle gains variety without any API
cost or unpredictable random choice.
