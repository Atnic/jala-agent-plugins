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

## Microsoft Office–Codex Bridge

**Office Add-in**:
A Microsoft Office extension whose user interface is a web application hosted by an Office client.
_Avoid_: Codex plugin, when referring to the component loaded inside Excel or Word

**Office action**:
A request to inspect or change the active Excel workbook or Word document through the Office Add-in.

**Connected Office document**:
An open Excel workbook or Word document that has an active connection from its Office Add-in to the Codex bridge.
_Avoid_: active document, when several documents can be connected

**Codex bridge**:
A local service connecting an Office Add-in to a Codex conversation so Codex can work with the active Office document.
_Avoid_: Office plugin, when referring to the service between Office and Codex
