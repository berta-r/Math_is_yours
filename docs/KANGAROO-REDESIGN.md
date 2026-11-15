# Kangaroo Studio · child-first redesign brief

Status: **implemented on `ui/kangaroo-studio` (2026-11-15)**. This document records the design gate used before implementation. Review the structure and language before changing the app. The existing offline tutor, stored progress, answer gate, hints and deterministic grading remain the product foundation.

## Audience and promise

A student roughly 9–14 years old should be able to open a saved notebook, understand what to do within five seconds, and complete one exercise without learning dashboard vocabulary. A teacher or parent can inspect progress, but that is a secondary route. The page must stay usable offline on the UNO Q and in the browser over USB or Wi-Fi. The UI must not invent mathematical explanations or claim that provisional mastery is certain.

Product promise: **"Solve a math problem, one thought at a time."** The app begins with a real exercise, not a marketing hero. The child's work is the hero.

## Candid review of the present interface

| Before | After | Why |
| --- | --- | --- |
| Landing page spends most of the first phone screen on a large headline and feature claims; the actual start button sits lower. | Show a short welcome, nickname and one obvious **Start practising** action in the first viewport. | A child came to do a problem, not read a pitch. |
| Default nickname is "Explorer" and the action says "Open my notebook". | Ask for a nickname once; button says **Start practising**. Returning users see **Continue as [name]**. | The action should predict the immediate next screen. |
| "Practice", "Knowledge map", "Notebook", "diagnostic", "independent evidence" and "provisional estimate" appear in the child's flow. | Child navigation: **Solve**, **My path**, **My work**. Technical model terms live behind **How progress works** for adults. | The child should not have to decode research terminology. |
| The current exercise is framed by three headings: page title, card title and skill label. | One exercise header with a progress marker and concise topic, then the problem. | Repeated hierarchy pushes the question down. |
| A dark recommendation card and a path card compete with the exercise on desktop; on mobile they create a long tail. | Show a single **Next problem** card after feedback. Move the full path to its own screen. | The next action matters after the current one is finished. |
| Step choices are small, dense rows inside a nested box; several feedback and helper messages appear below. | One thinking question per screen with 3 generous answer choices and immediate feedback in place. | Reduces scanning and keeps the child focused. |
| Hint, review answer and explain solution are visible together, even while some are disabled. | Show **Get a hint** during reasoning. Reveal answer and explanation only when the existing gate allows them; explain the prerequisite beside the locked action if necessary. | Disabled controls appear broken, especially to children. |
| The mobile knowledge graph compresses labels until they are barely readable. | Start with a readable skill path/list. Open a focused map as an optional exploration view with large tap targets. | A graph should make relationships clearer, not become a dexterity task. |
| A first-time notebook shows three zero counters and an empty history. | Show **Your first problem will start your notebook**, then the student's first attempt and later progress. | Empty metrics feel like failure before the child begins. |
| Status prose repeats generic guidance and exposes implementation details. | Status names the current event: **Checking your answer…**, **Your idea is saved**, **Try a different plan**. | Feedback should answer what happened and what to do next. |
| UI mixes text links, arrows, symbols, outlined circles and changing button styles. | One button system, one icon family, consistent use of an arrow for forward navigation only. | The meaning of an action should stay stable. |
| Current desktop and mobile browser checks pass, but some controls are reported as unresponsive by the user. | During implementation, inventory every control and verify action, loading, success and error states in the browser. | This is a reported usability problem, not yet a diagnosed defect. |

## Direction: the student's desk

The visual identity is a professional learning product with enough energy for a child. Signature colour: **Kangaroo Blue `#3254E8`**, used for the primary action, selected state, current step and focus indication. White text on this blue has a calculated contrast ratio of **5.88:1**. Background: warm paper `#FFF9EE`; primary ink `#17251F`; white exercise surface; restrained pale blue for selected options. A small apricot can mark a hint, but it must not become a second competing CTA colour. Correctness uses explicit words and icons alongside colour.

Type: a highly readable local system sans for instructions, questions and answers; a warm serif for a small number of display headlines. No web font request. 16–18px body text, 20–26px problem text, 48px minimum option/button height, 24px minimum between major groups. Avoid all-caps microcopy below 14px and long italic passages. Numbers in progress counters use tabular figures. One radius scale: outer panel 16px, inset card 10px, padding 24px, so inner corners never approach the outer radius.

The brand mark can be a simple typographic `k.`. Do not add stock photographs, decorative mascots, unverified claims or animated graph effects. The actual question, answer choices, diagram and thinking process are the product visuals.

## Information architecture

1. **Start:** nickname or returning profile, one promise, one action. No feature badges.
2. **Solve:** problem first, three thinking steps or a short free-text idea when no authored steps exist, then answer choices, then feedback and next action. The existing reflection and answer rules remain intact.
3. **My path:** one recommended next skill, a readable skill list and an optional expanded map. A selected skill has evidence and a clear **Practise this skill** action.
4. **My work:** recent exercises and reviews. Export and model-method details sit under an adult-facing disclosure, away from the child's primary route.

Navigation should always show where the child is, preserve the unfinished problem when switching screens, and allow a direct return to it. On a phone use compact three-item navigation with words; do not rely on icon meaning alone.

## Exercise storyboard

```text
[ kangaroo studio ]                         [ Solve | My path | My work ]

Problem 2 of 5   ·   Addition
How many beads remain?
[ Real question text / original diagram at readable size ]

Step 1 of 3: Understand
What changed in the story?
[ Choice, full width ]
[ Choice, full width ]
[ Choice, full width ]

[ Get a hint ]                    [ Next step, after a correct choice ]
```

On desktop, the problem and step can occupy a wide main column; a small secondary column may show the current topic and progress only. On a phone, one column with the problem and current step within the first content screen after the header. Do not put the full map, path, or recommendation beside an unfinished problem. For image-based M3Kang items, the original image is a first-class part of the question with a reliable full-screen enlarge control.

State sequence: **loading problem → reading → thinking step → step feedback → answer choices → checking answer → answer feedback → next problem**. Each state has a specific action and visible response. Wrong thinking choices can be retried; mistakes are framed as a chance to revise the approach. The answer key still follows the existing server gate. Keyboard focus moves to the new step or feedback without jumping the entire page unnecessarily.

## Motion and responsiveness

Only useful feedback moves: a pointer press responds in 120–160ms; selected choices change state immediately; final answer feedback may take up to 500ms to arrive and settle. No keyboard-triggered animation, scrolling reveals, bouncing cards, idle loops or animated graph. Respect reduced motion. Keep all significant controls at least 44×44px and verify at 320, 390, 768, 1024 and 1440px. The UI must render with no external assets or network calls.

## Twenty-point pre-implementation gate

Legend: **F** = current interface fails or meaningfully falls short; **P** = partial; **Y** = current interface meets the rule. The target column is the design acceptance criterion, not a claim about implemented code.

| # | Rule from reference | Now | Target acceptance criterion |
| --- | --- | --- | --- |
| 1 | Delete filler badges | F | No decorative feature chips or numbered eyebrow labels in the child's flow. |
| 2 | Drop redundant labels | F | One label per meaning; no repeated page/card/skill title. |
| 3 | Unitalicize random words | Y | Italic only if it carries a consistent typographic role; default none in learning UI. |
| 4 | Mono only where needed | Y | No monospace in student UI except mathematical/code content that requires it. |
| 5 | Use a design system | P | Document tokens for colour, type, spacing, radius, borders and states; use them everywhere. |
| 6 | Show the actual product | F | Start screen shows a real problem/step preview or enters the real exercise immediately. |
| 7 | Enlarge the main feature | P | Problem and its diagram dominate; readable at phone width without zoom. |
| 8 | Group with spacing | P | Problem, thinking step, answer and feedback are distinct groups with stable spacing. |
| 9 | Make headlines specific | F | "Solve a math problem, one thought at a time" or similarly concrete text. |
| 10 | Emphasize the CTA | P | Exactly one visually primary action in each state; secondary actions stay quiet. |
| 11 | Add an accent colour | P | Kangaroo Blue `#3254E8` is the unmistakable signature across key states. |
| 12 | Keep icons consistent | F | One icon set/style; no mix of arbitrary glyphs to indicate actions. |
| 13 | Remove embellishments | P | No decorative status dots, filler punctuation or effects without a learning purpose. |
| 14 | Inner radius = outer − padding | P | Radius hierarchy is consistent; inset surfaces never look rounder than containers. |
| 15 | Improve text contrast | P | Body and muted copy meet WCAG AA; blue/white primary is 5.88:1; test every state. |
| 16 | Wrap headlines properly | P | No orphan words or broken labels at 320 and 390px; problem text wraps naturally. |
| 17 | Align by eye, not pixels | P | Icon/text/button baselines checked visually at all key widths. |
| 18 | Use tabular nums | P | Progress, counts and steps use tabular figures. |
| 19 | Add loading states | P | Every request shows local, specific pending state and recovers on error. |
| 20 | Animate useful feedback | P | Motion confirms press, choice and feedback only; reduced-motion works. |

Implementation must not begin until the new layouts can be checked against all twenty targets. Completion requires a browser pass of the actual task flow, including a child-sized phone view, image questions, empty history, wrong answers, hints, keyboard, reduced motion and offline requests. Functional failures reported by the user are recorded for that pass; they are outside this design-only step.

## Implemented visual direction and verification

The reference led to an original blue typographic opening and large black display lettering. The live exercise is the main product visual immediately after starting. The primary action is visible in the first 900px viewport at 320, 390, 768, 1024 and 1440px, and none of those widths scroll horizontally. The three child-facing routes are Solve, My path and My work. The full recommendation and route moved out of the unfinished exercise. My path starts with readable, actionable skill rows while retaining the interactive map. Disabled answer-review actions are hidden until the existing server gate permits them.

Chrome checks at 1440 and 390px found no page JavaScript errors. A mobile-width flow completed all three thinking steps, chose an answer, selected a map skill and returned to a new exercise without horizontal overflow. All 48 student app tests pass locally. Physical touch, board visual review, educator copy review and the user-reported unresponsive controls still need direct validation with the actual device; this redesign did not claim those checks.

## 2026-11-15 interface review against the 20 rules

The black-framed version made the problem legible but let borders, duplicate labels and the oversized workshop heading compete with it. The review removed black borders from surfaces and controls while retaining a blue keyboard focus ring. It removed the giant decorative wordmark, extra floating cards, visible grid lines, numbering labels and the offline status dot. The blue remains the signature for the main action, selection, focus and next-step indication. The problem is now the largest object in the active workspace.

| Rules | Review result |
| --- | --- |
| 1–4, 13 | Decorative badges, duplicate index labels, extra wordmark and floating cards removed; no arbitrary italic or monospace typography. |
| 5, 11, 12, 14 | Blue and neutral tokens are shared; button roles and radii are consistent; arrows indicate forward actions. |
| 6–10 | The live problem appears immediately after entry; it leads Solve; spacing groups thinking, choices and feedback; one primary start action. |
| 15–18 | Text uses dark-on-light contrast; blue button has the previously calculated 5.88:1 white-text contrast; headings wrap at narrow widths; progress numbers use tabular figures. |
| 19–20 | Busy state and step feedback remain visible; only short pointer feedback moves, with reduced-motion support. |

Other improvements: the workspace title is smaller, the current skill replaces repeated labels, locked review controls stay hidden until permitted, and the current-exercise recommendation is hidden when it would only duplicate the path. Browser QA is still required after this revision; physical touch, educator review and the user-reported control issues are not certified by the visual pass.

## 2026-11-15 flat-surface correction

The white landing card and the pale-blue thinking card are gone. The nickname field is transparent over the blue opening and has a black underline, with a blue focus state. The floating “What remains?” arithmetic preview was only decoration and has been removed. Solve, My path and My work use open spacing and thin separators in place of white cards; the graph keeps its dark canvas because it is the interactive map itself. The first real problem follows the start action.

The final answer produces a large green or red inline signal. Its circle and message enter through opacity and transform; the symbol briefly scales. Pointer presses get a short transform, while reduced-motion preference keeps both responses static. The existing live text feedback continues to announce the actual result. Chrome checks at 390 and 1440px have no horizontal overflow or page errors; a real sample problem reached both wrong and correct final-answer states. All 75 current student-app tests pass. Board and physical touch review remain pending.

## 2026-11-15 typography and copy correction

The exercise screenshot exposed too many competing type levels: the blue workspace title, topic, process headline, scope sentence, step labels and live question all claimed attention. The landing screenshot repeated the start invitation in a large headline, explanatory paragraph, form heading and button; its pale footer interrupted the blue page. The form and headline also had different left edges.

The revised hierarchy uses one Arial family and four practical levels: display title on entry, live problem or section heading, current thinking question, and body/control text. The workspace heading, topic and process title remain available to assistive technology but are visually quiet. The exercise starts with its actual problem below compact navigation. The scope sentence and pre-answer gate copy are hidden visually; the child still receives real step feedback and error messages. The landing keeps only brand, promise, nickname, start action and a short local-privacy note. It is blue edge to edge, and the start action is transparent with a bottom rule. A click listener that had been attached to the entire body is scoped to the navigation buttons, so ordinary exercise clicks no longer trigger a view refocus.

Chrome checks at 320, 390, 768, 1024 and 1440px show the start action inside the first 900px and no horizontal overflow. Desktop and phone screenshots show the aligned entry form and problem-first exercise. A sample completes both wrong and correct feedback states without JavaScript errors. The 89 available student-app tests passed during this review. Physical board and touch review remain outstanding.

## 2026-11-15 screen-by-screen design review

| Screen | Professional critique | Applied correction |
| --- | --- | --- |
| Entry | The visible “Nickname” label repeated the input placeholder, and the local-storage note added a second explanation before the only action. | Removed both lines. The input keeps an accessible name; the display title, underline field and transparent start action remain. |
| Solve | A pale canvas, rounded active tab, tinted answer rows and multiple message surfaces made one exercise look like several unrelated components. | Extended the entry blue across the workspace, changed the active tab and answer rows to plain underline states, and kept green/red only for meaningful result feedback. |
| My path | The recommendation, route title and first skill repeated the same topic; ten skill tiles and a large dark graph competed for attention. | Reduced the route title to “Learning path”, removed repeated explanatory copy from sight, flattened the skill list, and placed the functional map inside a disclosure with the same blue and black system. Selecting a skill opens its detail. |
| My work | A pale page and separately framed metrics looked detached from the first screen. | Made the page blue, with one heading, tabular counts, plain separators and a transparent download action. |

The working palette is Kangaroo blue `#849fc4`, near-black text and cobalt `#3254e8` for focus/selection. Green and red are reserved for answer feedback. Arial is the one type family. Open spacing and thin rules form the shared component language; the graph and answer flow retain their behaviour. Desktop and phone Chrome screenshots show no JavaScript errors or horizontal overflow. Browser interaction verified skill selection and return to Solve, and both wrong and correct answer states remained visible. The local application suite passed 105 tests with one skip.
