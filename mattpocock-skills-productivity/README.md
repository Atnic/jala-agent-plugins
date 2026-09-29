# Matt Pocock Skills: Productivity

A Codex plugin that packages the seven skills in Matt Pocock's general
`Productivity` collection. It focuses on planning, learning, communication,
handoffs, questionnaires, and writing for agents.

## Included skills

- `grill-me` and `grilling`: interview through a plan or idea.
- `handoff`: create a handoff document for another agent.
- `teach`: teach a topic in a stateful learning workspace.
- `to-questionnaire`: turn unanswered questions into a questionnaire for someone else.
- `wait-what`: re-explain a message in simpler language.
- `writing-for-agents`: write skills and other documents agents use.

The source skills and their supporting files are copied into one `skills/`
root so Codex can install them as a single plugin. The MIT notice in
[`LICENSE.mattpocock`](LICENSE.mattpocock) applies to the upstream skill
material; it does not cover the separately sourced AI Hero logo. The skills
retain upstream `agents/openai.yaml` metadata. This is a community package
maintained by JALA, not an official Matt Pocock plugin.

The plugin mark uses the AI Hero logo from its [brand page](https://www.aihero.dev/brand),
with light and dark SVG variants. See [ASSETS.md](ASSETS.md) for the asset
source and license scope.

See [UPSTREAM.md](UPSTREAM.md) for source revision and refresh notes.

## Install in Codex

From the JALA Agent Plugins marketplace:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin add mattpocock-skills-productivity@jala-agent-plugins
```

For a local checkout, add its absolute path as a marketplace and install
`mattpocock-skills-productivity@jala-agent-plugins`. Start a new Codex task
after installation so the skills load.

## Upstream

Source: [mattpocock/skills](https://github.com/mattpocock/skills),
`skills/productivity/`. The upstream project is MIT licensed; see
[LICENSE.mattpocock](LICENSE.mattpocock).
