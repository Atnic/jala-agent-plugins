# Prototype verification

## Read-back checklist

- Trigger type is the intended one.
- Action type is correct: navigate, overlay, or swap.
- Destination ID exists and names the expected frame/component.
- Transition type, duration, and easing are supported and deliberate.
- Existing unrelated reactions remain present.
- Scroll direction and clipping match the viewport's geometry.

## Visual checklist

Screenshot every relevant resting frame. Check that controls remain visible, overlays have enough space, scroll containers do not clip important content, and component states use the correct variables and typography.

## Playback boundary

A read-back validates the stored prototype graph, not the end-user playback. When the task requires confirming a click path or transition timing, preview the prototype in Figma Desktop after the bridge changes and report any behavior that cannot be verified through the local MCP response.
