# Math Is Yours design rules

The rules the product owner has set for the student app (`student_app/assets/`). Each rule has its reason, so an agent that was not in the review can apply it to new screens. When a rule here conflicts with an older brief (for example [MIY-REDESIGN.md](MIY-REDESIGN.md)), this file wins. CSS is layered: append a new "Studio NN" block at the end of `style.css` and override; do not rewrite old layers.

## Audience

- **The reader is a child of 9–14. Every message the child must read is large and visual.** Feedback after an action (a thinking-step check, the answer result, a hint, an answer or an explanation) is a framed band with a glyph and a headline of at least 22px and a body of at least 19px. Never a small line of text. *Why:* children do not read small text, and the feedback is the teaching moment; if it is easy to miss, the step was wasted.
- **No research vocabulary in the child's flow.** Words like BKT, mastery estimate, Elo, prerequisite graph or confidence stay out of buttons, headings and feedback; technical notes live behind disclosures ("About these learning estimates"). *Why:* the child needs to know what to do next, not how the model works; teachers and the jury can open the note.
- **The UI language follows the open problem's language** (`eng` → English, `cat` → Catalan), through the `STRINGS` table and `t()` in `app.js` and the server's message tables. Every new string gets both entries. *Why:* a Catalan problem with English buttons splits the child's attention between two languages.

## Type

- **Minimum 16px for any visible text; 18px for anything about the problem** (statement, options, step questions, card categories, tree names). This includes SVG text at its rendered scale. *Why:* readability for young readers on a small board screen; it is checked in the Playwright audits.
- **One type family: Archivo, bundled** (`assets/fonts/`, see D-014). Display titles are weight 900 with the blue square period; section headings are weight 700, sentence case; uppercase only on the Understand / Plan / Check step rail. *Why:* one family keeps the page calm; uppercase everywhere shouts and is slower to read.

## Controls

- **3px ink frames, square corners.** Standalone buttons lift on hover with a 4px hard shadow; options in a list (answer choices, step options, goal buttons) do not lift, they change fill and border. Press scales to .98. *Why:* lifting signals "this one thing is an action"; a list where every row jumps is noisy.
- **Two border weights only:** 3px for controls and bands, 1px for dividers. The one exception is the strong 3px rule that separates blocks in Solve (below).
- **Action hierarchy:** primary = filled ink, secondary = 3px frame on transparent, tertiary = underlined text. A disabled primary stays at opacity .45 with no helper text under it. *Why:* one obvious next action; helper copy under buttons was read as an error.

## Colour

- Ink `#080d15`, cream reading surface `#f6f4ed`, header blue `#8a9ed4`, accent `#3254e8`, selected `#dce4fa`.
- **Green `#13754c` only for done / correct, red `#b2293d` only for wrong.** Blue marks the path and the goal. *Why:* if green or red appear for decoration, the child cannot trust them as feedback.

## Solve layout

- "Change problem" at the top-left of the column; the Understand / Plan / Check rail directly above the statement (hidden when the problem has no thinking steps); the statement full width.
- A 3px ink rule (32px above and below) between the statement block and the thinking question, and again before "Choose your answer". *Why:* the statement and the question about it were read as one paragraph.
- No optional notes when the problem has thinking steps (the free-text note is only the gate for problems without steps), and no helper copy under buttons. *Why:* every extra control on the page competes with the problem.

## My path

- **In the skill tree, colour and the corner glyph carry the state; there is no legend and no state line under the names.** Got it = solid green, white text, ✓; getting there = light green fill with green border, ↗ (time to review: ◷); not tried = cream with ink border, no glyph; on the way to the goal = selected blue fill with accent border; the goal = solid accent, white text, cream corner square. Names are 22px bold (20px when a name needs three lines). Each node's aria-label keeps the state words. *Why:* a legend and 16px state labels were small text the child had to decode.
- **Problem cards are whole buttons** with the order number (28px, 900), the category, and the difficulty with its level at the bottom; no question text. The card is tinted by difficulty (easy green, medium blue, hard ink, all at 14% opacity), the goal card has an accent border, a solved card shows ✓ top-right. *Why:* one large target per problem, and the difficulty is visible at a glance without reading.

- **The tree is the control.** Clicking a skill in the tree chooses it as the goal and shows the problem plan; there are no separate goal buttons and no skill panel. Why: one gesture, no duplicated controls, and the cards are the way to practise.
