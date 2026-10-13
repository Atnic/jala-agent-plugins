# JALA Agent Plugins

## Odoo JALA Web

**Trainer**:
The person teaching the agent an Odoo procedure through explanation and browser demonstrations.

**Learned workflow skill**:
A reusable procedure produced from a trainer's teaching for that trainer's personal use.

**Browser demonstration**:
A trainer's walkthrough of an Odoo procedure. The agent knows only the browser states it explicitly inspects and the explanations the trainer supplies; a demonstration does not imply continuous observation.

## 9Router JALA

This context distinguishes the model route exposed by JALA's gateway from the Codex connection and plugin capability that use it.

**Gateway model alias**:
The name exposed by the hosted JALA 9Router for a model route. It identifies a model choice available to a client, independently of the connection the client uses to reach the gateway.

**Codex provider**:
The connection Codex uses to send inference requests to a model service. It is distinct from the gateway model alias selected for a request.

**Plugin skill model**:
The model a 9router capability skill selects for its own API request. It is independent of the model configured for Codex itself.

**Codex provider setup**:
Configuration that directs Codex's own inference requests to the JALA 9Router gateway. It is independent of the 9router capability skills' API requests.
