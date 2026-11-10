# Product note — Report → Fix

## Who loses most when a question is broken?
The student preparing under time pressure loses the most: a wrong key or incomplete option can cost marks, create doubt in a correct concept, and waste revision time. Repeated exposure makes the harm larger. The console therefore groups duplicate reports, ranks answer-key and missing-content cases first, then other faculty-only cases, and uses recurrence as a tie-breaker. It previews the exact change and student-facing explanation.

## What should AI never auto-apply?
It should never invent a diagram, distractor, missing premise, syllabus classification, or replacement educational explanation when the source does not establish the answer. It should not auto-apply answer-key, solution, option, missing-data, type, or syllabus changes. The implementation restricts auto-eligibility to spelling, noise, exam-reference removal, and markup-leak cleanup, with exact source matching and a 0.95 confidence floor. Faculty approval records a demo decision; it does not publish a production correction.

## Week-one metric
**Verified defect precision:** among cases marked as defects by triage and reviewed by faculty, the percentage confirmed as genuine defects. Track it separately for auto-eligible and faculty-routed cases; false positives create review load and can undermine trust.

## Beyond the brief
Add a question-level impact score using exposure (how many students attempted the item), recurrence, and assessment proximity. A defect reported by one student on a high-traffic mock test may deserve faster attention than five reports on an archived practice item. Keep the score explainable and never let it replace academic verification.
