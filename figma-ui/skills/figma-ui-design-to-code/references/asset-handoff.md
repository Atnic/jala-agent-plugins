# Asset handoff

## Asset workflow

1. Identify every visible image, SVG, icon, and logo in the target tree.
2. Prefer existing project assets when they are exact matches.
3. For a Figma-only static asset, use `figma_read` with `export_svg` or `export_image`.
4. Save the returned asset in the project's normal asset directory.
5. Reference the local file from code and preserve its intrinsic dimensions/aspect ratio.
6. Verify the rendered slot against the Figma screenshot.

Do not use a screenshot of the whole frame as a substitute for individual assets. Do not leave base64 blobs or temporary bridge URLs in production code unless the project explicitly uses that format.

## Icons

If the design uses an icon from a code library already installed in the project, use the exact matching icon and verify its stroke/fill and size. If no exact code asset exists, export the specific Figma vector and keep its viewBox/root dimensions intact.

## Dynamic imagery

Images supplied by an API, user upload, or runtime state stay dynamic. Use the Figma asset only to understand the slot's crop, aspect ratio, and fallback treatment.
