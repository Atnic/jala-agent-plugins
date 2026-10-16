# JALA addon source and workflow map

Source reviewed: user-supplied `jala-odoo-custom-addons` repository, clean revision
`2c1d9359124bbaee20c067c8cea455b4aed1d4b8`, on 2026-10-15. This is a **source
snapshot**, not a production installation inventory. Confirm installed addons
and current schemas with `discover`; use the user's available source checkout
or its authorized repository when exact method implementations are needed.
The plugin does not require every user's machine to have the author's checkout.

[jala-addons-index.json](jala-addons-index.json) indexes 104 selected addon manifests,
including 63 `jala_` names, and 535 Python model declarations. It includes
manifest dependencies/versions and source locations for model extensions and
public method declarations. Select the relevant addon/model from JSON; do not
load the whole index into context. The source includes third-party addons as
well as JALA-specific work. A directory name alone does not establish authorship.

The index is static: it excludes tests, migrations, and build outputs, can include
unimported declarations, and does not reconstruct Odoo's registered inheritance
order. A public method entry is a source locator, not a callable contract or an
authorization whitelist. Recheck the source revision and installed versions
before applying a snapshot-specific workflow. No addon Python code was executed
to build the index, and no addon implementation is bundled by this plugin.

## Find the relevant operational area

| User's topic | Addon candidates in this repository | Models to inspect |
| --- | --- | --- |
| Vendor bills, customer invoices, payment dates | `ys_core`, `jala_account_move`, `jala_invoice`, `jala_approvals` | `account.move`, `account.move.line`, `account.payment`, `account.payment.register`, `jala.account.move.payment` |
| Purchase orders and purchase requests | `purchase_request`, `purchase_request_tier_validation`, `jala_approvals`, `jala_partner_purchase_vendorbill`, `jala_purchase_sale_bridge` | `purchase.order`, `purchase.request`, `approval.request`, their approval/line models |
| Expenses, advances, realization, settlement | `ys_core`, `jala_expenses`, `jala_expense_analytic_realization`, `jala_approvals` | `hr.expense`, `hr.expense.sheet`, `jala.payment.method`, `jala.expense.realisasi`, `popup.expense.register.payment` |
| Approval Review and delegation | `jala_approvals`, `jala_approval_delegation`, `base_tier_validation` and its adapters | `approval.request`, `approval.category`, `approval.approver`, `approval.delegations`, document-specific approval models |
| Farm budget requests, rent, disbursement | `jala_farm_budget_request`, `jala_farm_budget_fa`, `jala_farm_po_rent`, `jala_farm_budget_management` | `helpdesk.ticket`, `disbursement.rent.farm`, `jala_farm_po_rent.purchase_order`, budget/approval lines |
| Budget utilization and limits | `ark_account_analytic_booked`, `ark_account_limit_budget`, `ark_purchase_request_budget`, `jala_report_budget` | `crossovered.budget`, `crossovered.budget.lines`, `account.move`, `purchase.request` |
| Stock and inventory valuation | `jala_stock`, `jala_automatic_inventory_valuation`, `jala_validate_stock`, valuation/report addons | `stock.picking`, `stock.move`, `stock.valuation.layer` and applicable report models |
| Accounting Jack and virtual accounts | `accounting_jack` | `account.move`, `account.payment`, `virtual.account`, `jack.va.record` |

These are starting points. Multiple installed addons can extend the same model,
and further dependencies can live outside this source repository. A Finance
request about a standard-named model therefore still needs JALA source context.

## Observed contracts that change execution decisions

**Purchase approval submission.** In
`jala_approvals/models/purchase_order.py:103`, `purchase.order.action_req_approval`
rejects zero totals, updates approval status, rebuilds document approver lines,
selects approval configuration by company/department/job/cross-department inputs,
creates linked approval documents, and can send email. Inspect `employee_req_id`,
department/job, cross-department data, `info_status`, `is_req_app`, and approver
links for the actual record. Submitting a PO for approval is a workflow operation;
writing its `state` alone does not perform these steps. A retry can duplicate
approval work or notifications.

**Bill/invoice approval.** In `jala_approvals/models/account_move.py:42`,
`account.move.action_req_approval` requires `invoice_date`, sets `state_approval`
to `progress`, and creates approval requests based on company/department
configuration and approval levels/amount ranges. `state`, `state_approval`,
`info_status`, and `is_req_app` represent different facts. Inspect them together;
do not equate a posted invoice with a completed JALA approval.

**Approval decisions.** `jala_approvals/models/approval_request.py:128` contains
`action_approve(self, approver=None)` and `:969` contains `action_refuse`.
These are large, document-specific implementations with approval-level logic,
activity updates, and effects on linked business documents. Their signatures
alone do not establish a safe RPC call for every document type. Read the branch
for the actual linked document and its inherited methods; use the current user's
legitimate Approver role. Internal `sudo()` usage does not grant the agent
permission to bypass the business workflow.

**Expense workflow and settlement.**
`jala_approvals/models/hr_expense_sheet.py:93` overrides submission and can send
email; `:146` implements approval submission and rebuilds approval records.
`ys_core/models/expense.py:151` and
`jala_expenses/models/hr_expense_sheet.py:112` implement `register_payment` logic
that returns a settlement wizard/action with context. Returning an action is not
proof that a payment was registered. Resolve the wizard's actual required values
and business method before executing a user-authorized settlement. The source
also has responsible-validation checks in `ys_core/models/expense.py:173`.

**Payment-method reporting.** `jala_expenses/models/hr_expense.py:14` associates
expense lines with `jala.payment.method`. The sheet's computed `amount_cc`,
`amount_gocorp`, `amount_adv`, `amount_df`, and `amount_rmb` summarize configured
payment-method categories. `amount_rmb` is calculated for payment-method name
`RMB`/`rmb`; do not infer a currency from this field name. Verify the company's
actual currency and method records before explaining totals.

**Payment tracking and invoice links.**
`jala_account_move/models/account_move.py:167` extends posting, and `:179`
extends reset to draft, to maintain invoice references for company code `IMU`.
The same file adds `last_payment_date`, `payment_dates_display`,
`purchase_invoice_ref_ids`, and `sale_invoice_ref_ids`.
`jala_account_move/models/account_payment_register.py` extends reconciliation to
create `jala.account.move.payment` records. Preserve the normal posting and
reconciliation flows; manually changing a payment-date field is not settlement.
