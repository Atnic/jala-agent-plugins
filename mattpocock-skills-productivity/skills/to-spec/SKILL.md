---
name: to-spec
description: "Turn the current conversation into a spec based on what you've already discussed."
---

This skill takes the current conversation and relevant project documents and produces a spec. Do NOT interview the user; just synthesize what you already know.

## Process

1. Read the relevant project documents to understand the current state, if you haven't already. Use the project's glossary vocabulary throughout the spec, and respect any decision records in the area you're touching.

2. Identify how the team will tell whether the plan worked. Use observable outcomes and any existing measures agreed in the conversation. List unresolved measures as open questions in Further Notes.

3. Write the spec using the template below. Save it where the project keeps specs, or use `docs/specs/<topic>.md` if there is no convention. Publish it to a tracker or shared workspace when the user requests it.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A numbered list of user stories. Each user story should be in the format of:

1. As a <person or role>, I want <outcome>, so that <benefit>

<user-story-example>
1. As a workshop participant, I want the materials in advance, so that I can prepare
</user-story-example>

Cover the people and outcomes affected by the plan.

## Delivery Decisions

A list of agreed decisions about how the work will happen. This can include responsibilities, handoffs, constraints, and how people will use the result.

Include a short excerpt from a prototype when it captures a decision more precisely than prose.

## Success Criteria

List the observable outcomes that show whether the plan worked and how the team will assess them.

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>
