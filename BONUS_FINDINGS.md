# Bonus QA finding — unreported question

**Question ID:** `68dea87d387eea3d0d95fbe3`  
**Subject / chapter:** Physics / Electrostatics  
**Report status:** No student report in the supplied 44-report dataset.

The stem contains an empty MathML identifier inside the exponent for the unit of α:

```html
<mi> &alpha; </mi><mo>=</mo><mn> 1 </mn> ... volt
<msup><mi></mi><mrow><mo>&minus;</mo><mn> 1 </mn></mrow></msup>
```

The intended unit is `V⁻¹` (or `volt⁻¹`), but the MathML exponent has an empty base `<mi></mi>`. This is a low-severity markup/notation defect candidate: the rendered display should be checked in the target browser, and the MathML should be corrected so the inverse-voltage unit is structurally valid. The mathematical solution and keyed answer A (5 V) are otherwise consistent:

`αV² + V − 30 = 0`, with positive solution `V = 5 V` for `α = 1 V⁻¹`.

**Why not auto-edit the benchmark?** The question is unreported and the precise intended markup can be confirmed against the source authoring record. It is surfaced as a QA finding rather than silently modifying the source data.
