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

## Scheduler

**Scheduled continuation**:
A saved prompt and recurring schedule for continuing an existing agent session.

**Target session**:
The existing Codex or Claude conversation that a scheduled continuation resumes, identified by its agent type and session ID.

**Scheduled occurrence**:
A time at which a scheduled continuation is due.

## Felix Agent

**Felix Owner**:
The person who controls a Felix installation and its protected capabilities.

**API Contact**:
A contact represented by an API-channel identity; it is distinct from the Felix Owner.

**Built-in Felix skill**:
A skill supplied with Felix that the Owner cannot change.

**Custom Felix skill**:
A separately authored skill added to a Felix installation.

## App Store Connect

**App Store Connect API key**:
A key pair issued by App Store Connect to authorize REST API requests. The key type and assigned role determine which API resources and actions it can access.

**Individual API key**:
An API key associated with one App Store Connect user; it follows that user's roles and app access, but cannot access Sales and Finance reports.

**Team API key**:
An API key with an assigned role that can access all apps in its App Store Connect team.

**App Store Connect API operation**:
An operation identified by its HTTP method and endpoint in Apple's App Store Connect API documentation.

**High-impact write**:
An App Store Connect API operation that deletes or revokes a resource, changes submission or release state, changes pricing or availability, or changes user access. It requires confirmation before execution.

## Google Play Console

**Play Console developer API**:
An official Google API for managing apps and related data in a Play developer account.

**Play Console API action**:
An operation-specific typed tool corresponding to one operation in an official Play Console developer API.

**Play Console user**:
A Google Account user with access to a Play developer account; API actions inherit that user's Play Console permissions.

**Play Console service account**:
A Google Cloud service identity added to a Play developer account and granted Play Console permissions.

**Play Console account profile**:
A named connection between an authorization identity and a Play developer account. The identity can be a Play Console user or service account.

**Play Console edit**:
A group of app changes staged for a Play developer account; the changes take effect when the edit is committed.

**Play Console edit commit**:
The action that applies a staged Play Console edit. It requires confirmation before execution.

**Play Console high-impact write**:
A direct operation that deletes a resource, changes user access or app signing, changes price or availability, refunds a purchase, or cancels a purchase or subscription. It requires confirmation before execution.

## Metabase JALA

**JALA Metabase instance**:
The shared JALA Metabase deployment at `https://metabase.jala.tech`.

**Metabase MCP connection**:
An OAuth-authenticated client connection to the instance’s built-in MCP endpoint at `/api/metabase-mcp`. Tool calls run as the signed-in Metabase user and follow that user’s Metabase permissions and the instance’s MCP tool access settings.

**Metabase content**:
Saved questions, dashboards, and collections in Metabase.
