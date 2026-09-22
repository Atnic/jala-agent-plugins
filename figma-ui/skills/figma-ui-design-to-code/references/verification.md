# Design-to-code verification

Compare the implementation with the Figma screenshot at the same viewport and device pixel ratio when possible.

## Inspect

- page/frame dimensions and responsive constraints;
- major region positions and flow direction;
- text content, font family, weight, size, line height, and wrapping;
- token-resolved colors, borders, radius, and shadows;
- icon and image geometry;
- component variants and states;
- focus, hover, disabled, empty, and error states when visible or requested.

## Fix order

Fix in this order so later measurements are meaningful:

1. wrong hierarchy or layout direction;
2. wrong container dimensions or spacing;
3. wrong typography and text wrapping;
4. wrong assets or icon geometry;
5. color, border, radius, and shadow details;
6. interaction/state differences.

Re-render after each bounded set of fixes. Sign off only when the requested screen or component matches closely and no in-scope asset or state mismatch remains.
