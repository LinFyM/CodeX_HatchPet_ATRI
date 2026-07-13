# ATRI look-direction mechanics

The 16 look frames are a curious, high-performance ATRI tracking something around the screen. They are not whole-body rotations and they are not a neutral idle loop.

## Coordinate semantics

- `000`: screen up.
- `090`: screen right.
- `180`: screen down.
- `270`: screen left.
- Intermediate angles advance clockwise in even 22.5-degree visual steps.

Screen left and right always mean the viewer's image edges.

## Natural movement chain

1. Coral-magenta pupils lead the target.
2. Eyelids and brows support the vertical component: upper lid opens slightly for up, lower focus and a small chin tuck for down.
3. The head follows with restrained pitch/yaw; the nose and visible cheek make left/right unambiguous.
4. Neck and shoulders absorb only a small fraction of the head motion.
5. Hair, ahoge, and side bows follow the head with subtle delayed overlap while remaining attached.

Feet, legs, pelvis, dress hem, and baseline stay registered. The torso may counterbalance a few pixels but must never translate, rotate, skew, grow, or shrink to fake a direction.

## Cardinal anchors

- Up: broadly frontal face, pupils high, chin lifted slightly; no sideways drift.
- Right: pupils, nose tip, and face surface clearly occupy the screen-right side of the head center.
- Down: broadly frontal face, pupils low, eyelids focused, chin tucked; no sleepy collapse.
- Left: the exact screen-left inverse of the rightward facial cue, with character identity and lighting preserved.

## Character and physics gates

- Expression remains alert, curious, and eager rather than vacant or frightened.
- Every frame keeps two connected arms, two connected legs, complete bare feet, three gold buttons, two bows, and one ahoge.
- Adjacent frames must advance monotonically; no direction reversal, sudden head-size change, or 157.5/180 and 337.5/000 boundary jump.
- No arrows, degree labels, replacement eyes, floating effects, shadows, props, or whole-body spin.
