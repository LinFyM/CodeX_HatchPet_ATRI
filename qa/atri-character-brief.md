# ATRI flagship pet character brief

This brief records the research and production decisions for the flagship Codex pet rebuild.
Official images are used only as temporary visual references and are not redistributed in the pet package.

## Canonical character evidence

- ATRI is a highly sophisticated, emotionally expressive robot girl salvaged from the seabed. She is
  visually almost indistinguishable from a human, has partial memory loss, wants to complete her former
  master's last order, is extremely curious and eager to learn, and proudly calls herself
  "high-performance".
- The story pairs that confidence with comic clumsiness: she earnestly tries to support Natsuki, but can
  still mishandle ordinary tasks. The pet should therefore feel capable, bright, affectionate, proud,
  and occasionally adorably deflated—not mechanical, cold, or generic.
- The visual identity is a warm ash-silver/blonde long-haired girl with one curved ahoge, small dark
  ribbon bows at both sides of her head, coral-magenta eyes, an oversized white sailor-dress, teal collar
  and cuffs with white trim, a red neck ribbon, gold buttons, and bare feet.

Official sources:

- Game character profile: <https://atri-mdm.com/en/character/?chara=atri>
- Game story and world: <https://atri-mdm.com/en/story/>
- Anime character profile: <https://atri-anime.com/character/atri.html>
- Anime episode summaries: <https://www.aniplex.co.jp/lineup/atri/story/>
- Official game gallery: <https://atri-mdm.com/gallery/>
- Official anime character PV index: <https://atri-anime.com/movie/>

## Flagship visual direction

- Style: premium anime chibi illustration, about 3.0–3.2 heads tall, clean cool-gray line art, controlled
  cel shading, expressive eyes, and a soft pearly hair palette. It should read as ATRI at a glance while
  remaining clear inside a 192×208 cell.
- Canonical model: one identity sheet governs every row. Face shape, eye color, fringe, ahoge, hair
  length, two side bows, sailor collar, cuffs, red ribbon, three gold buttons, dress hem, and barefoot
  design may not drift between states.
- Silhouette: the ahoge, long twin-flowing hair masses, huge bell sleeves, A-line sailor dress, and bare
  feet are the primary small-size recognition cues.
- Palette: warm ivory white, turquoise/teal trim, muted crimson ribbon, warm ash-silver hair with mauve
  shadows, coral-magenta eyes, dark navy-black bows, and restrained gold buttons.
- Rendering: complete opaque body in every frame, crisp antialiased edges, no cast shadow, no detached
  effects, no scenery, no text, and no transparent gaps through limbs or torso.

## State direction

- Idle: calm breathing, soft hair sway, tiny blink, and a restrained proud smile.
- Running right: a real eight-frame two-step sprint cycle. Frames 0–3 are one leg's contact/down/pass/
  flight phases; frames 4–7 repeat those phases with the opposite leg. Near and far legs must be
  distinguishable through overlap and shading. Every frame is one complete body.
- Running left: framewise whole-body mirror of the approved right-running cycle, preserving temporal
  order.
- Waving: bright, eager greeting using only the arm and hand pose; no motion arcs.
- Jumping: joyful high-performance hop with anticipation, lift, apex, descent, and settle; no floor cue.
- Failed: the comic "high-performance but unexpectedly clumsy" contrast, shown through expression and
  posture only.
- Waiting: hopeful request for approval/help, with attentive eye contact and hands gathered near the
  chest; distinct from idle.
- Task running: focused internal processing with purposeful hand/eye/head motion; not locomotion and no
  floating UI.
- Review: close visual scrutiny followed by a small confident nod/smile; no magnifier or paper prop.
- Look directions: 16 clockwise head-and-eye directions with planted lower body, consistent scale, and
  readable cardinal axes. The ahoge and hair mass should support, not contradict, head orientation.

## Definition of success

- Valid Codex v2 package: 1536×2288 WebP, 8×11 cells, 192×208 each, 74 populated cells, transparent
  unused cells, and `spriteVersionNumber: 2`.
- All frames preserve one character identity and remain legible at in-app display size.
- Directional running is a visibly alternating two-step loop with no repeated-foot cadence, reversed
  limbs, detached anatomy, clipping, seams, or edge tearing.
- All nine standard states are immediately distinguishable and character-specific.
- All 16 look directions pass cardinal semantics, ordered-loop continuity, scale, baseline, edge, and
  transparency review.
- Left-half look frames preserve whole-frame mirrored anatomy and lighting under one consistent 2 px
  registration translation, avoiding both leg-shadow inversion and a 337.5/0-degree loop jump.
- Repository asset and local installation are byte-identical after final packaging.

## Non-goals

- No new application format, custom runtime logic, audio, text bubbles, or external props.
- No copying official images into the shipped package.
- No one-cell repairs or limb compositing across independently generated bodies.
