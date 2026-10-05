# Matt Pocock Skills: Engineering

A Codex plugin packaging all 20 skills in Matt Pocock's `Engineering`
collection. It covers planning and building software, codebase design,
debugging, testing, issue triage, research, and review.

The upstream files and supporting material are copied into a single `skills/`
root. See [`skills/README.md`](skills/README.md) for the full inventory. The MIT
notice in [`LICENSE.mattpocock`](LICENSE.mattpocock) applies to upstream skill
material, not the separately sourced AI Hero logo. See [ASSETS.md](ASSETS.md)
for the asset source and license scope. This is a community package maintained
by JALA, not an official Matt Pocock plugin.

## Setup and prerequisites

Run `$setup-matt-pocock-skills` in each target repository before the first
engineering workflow. It configures the issue tracker, triage labels, and
domain-document layout the skills expect. Local Markdown tracking is supported;
GitHub and GitLab tracking use their authenticated `gh` and `glab` CLIs,
respectively. Some workflows use subagents and require host support for them.

The Engineering router also points to skills in the Productivity collection.
Install `mattpocock-skills-productivity` to make the full set of routed skills
available.

## Install in Codex

From the JALA Agent Plugins marketplace:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin add mattpocock-skills-engineering@jala-agent-plugins
```

For a local checkout, add its absolute path as a marketplace and install
`mattpocock-skills-engineering@jala-agent-plugins`. Start a new Codex task after
installation so the skills load.

## Upstream

Source: [mattpocock/skills](https://github.com/mattpocock/skills),
`skills/engineering/`, release `v1.3.1`. See [UPSTREAM.md](UPSTREAM.md) for the
pinned source commit and refresh notes.
