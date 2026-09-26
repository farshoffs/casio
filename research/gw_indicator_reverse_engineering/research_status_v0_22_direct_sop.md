# GW/MPL reverse engineering — v0.22 direct SOP evidence

## Public-channel evidence

Public posts from MANKET 3 SOP INDICATOR describe the entry SOP explicitly.

One post states that all three SOPs on M3 are:
1. break the solid blue line;
2. crossing MPL B near/below;
3. Momentum Power Line changes color from red to green.

A newer post states the sell-side SOP as:
1. blue line crosses orange line;
2. candle breaks the blue line;
3. MPL Momentum changes from green to red.

The same channel also states:
- M15 is used to read trend direction;
- M1/M3 are used for entry confirmation and re-entry;
- if M15 candle is below the blue line, users should wait for M1/M3 sell SOP completion rather than entering immediately.

## Consequences

This invalidates several earlier assumptions.

### Blue line
Direct user overlay evidence identifies it strongly as SMA20(close).

### Red/green ribbon
The red/green component is not simply a delayed MA fill hypothesis. Public wording treats the Momentum Power Line color-state change as its own SOP condition.

### Orange line / MPL B
The public wording strongly suggests:
- an orange line exists separately from the blue line;
- "MPL B" is likely the orange/crossing component or closely related to it;
- the blue/orange cross is a distinct SOP from candle break and momentum-color change.

### MTF architecture
Current direct model:

M15:
- direction/trend context from candle position relative to blue SMA20.

M1/M3:
- SOP1 blue/orange (MPL B) cross,
- SOP2 candle break of blue SMA20,
- SOP3 Momentum Power Line color flip,
- entry only after all SOPs complete.

This is a much stronger reconstruction target than previous generic MTF MA alignment.

## Next target

Identify the orange/MPL-B formula first, then reconstruct the red/green Momentum Power Line color-state formula separately.

Do not assume the red/green ribbon is EMA/HMA/RMA vs lagged self; that hypothesis is now rejected.
