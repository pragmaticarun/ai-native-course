# Ex 15.1: set-of-marks and the invalid-action rate

A pixel agent says "click (x, y)"; a set-of-marks agent says "click [7]". Measure the difference.

`tests/screen.json` is the element list the M15 sandbox calendar page produced through
`gui_agents.MARK_JS` (boxes in CSS pixels, 1280x800 viewport). Write:

1. `annotate(elements)`: keep interactive elements (`role` in link/button/textbox) with a non-empty
   box, sort them in reading order (by `y` rounded to 10 px, then `x`), and number them from 1.
   Return `{mark: element}`.
2. `click_point(element)`: the centre of its box.
3. `invalid_rate(elements, targets, sigma_px, use_marks, seed)`: for each target name, simulate one
   click. Without marks the "model" estimates the centre with Gaussian error `sigma_px` in each axis
   (use `random.Random(seed)`, x error then y error per click); with marks it names the mark and we
   click its exact centre. A click is invalid if it lands outside every interactive box. Return
   invalid clicks / clicks.

`sigma_px` is a simulation knob for grounding error, not a property of any real model. The M15
worked example runs the same comparison in a real browser (`test_poor_grounding_costs_invalid_actions`).
