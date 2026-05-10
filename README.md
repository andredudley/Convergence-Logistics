# Convergence Logistics Company Fleet Manager Documentation

## Overview

`nms_fleet.py` is the core fleet management application for Convergence Logistics Company.
It provides a console-based operational interface for managing fleet assets, logging expedition activity, tracking spoils, maintaining unit financials, and reconciling inventory.

This document explains the fleet manager architecture, data model, user workflows, and operational behavior in detail.

## System Architecture

The application is implemented around three main components:

- `FleetDatabase`: handles SQLite persistence and schema initialization.
- `FleetLogistics`: contains business logic for fleet operations, expedition handling, finance, and inventory.
- `KorvaxInterface`: serves as the terminal UI and menu-driven interaction layer.

The application is intentionally self-contained and requires only Python 3 and the standard library.

## Startup and Initialization

When launched with:

```bash
python nms_fleet.py
```

the program performs the following startup sequence:

1. Creates or opens the SQLite database file `korvax_fleet.db`.
2. Ensures all required tables exist.
3. Verifies the singleton `player_state` row exists.
4. If the wallet has never been initialized, prompts the operator for the current unit balance.
5. Attaches the fleet manager interface and enters the main operation loop.

### Wallet Initialization

The fleet manager requires a starting balance before any operations can proceed.
This is enforced by the `player_state` table and the `initialize_wallet(amount)` workflow.

- The first balance set is recorded as a `Balance Set` transaction in `unit_ledger`.
- This initial balance can only be set once.
- Subsequent adjustments require reconciliation via the manual override function.

## Data Model and Tables

The fleet manager stores operational data in the following tables:

### `fleet_registry`

Tracks each frigate in the fleet:

- `frigate_name`: unique vessel identifier.
- `frigate_class`: one of `Combat`, `Trade`, `Exploration`, `Industrial`, `Support`, `Living`.
- `tier`: one of `C`, `B`, `A`, `S`.
- `recruitment_cost_units`: units spent to acquire the vessel.
- `recruitment_date`: automatic date of registry entry.
- `specialization` and `notes`: optional descriptive fields.
- `active_status`: status of the vessel, restricted to `Active`, `Damaged`, `Lost`, or `Retired`.

### `expedition_log`

Records expedition missions:

- `expedition_date`: mission launch date.
- `expedition_type`: `Combat`, `Trade`, `Exploration`, `Industrial`, `Balanced`.
- `duration_hours`: expected mission duration.
- `fuel_cost_units`: fuel expenditure for the deployment.
- `frigates_deployed`: number of frigates assigned.
- `expedition_result`: `Success`, `Partial`, `Failure`, or `Frigate Damaged`.

### `expedition_frigate_assignments`

Associates deployed frigates with each expedition via foreign key relationships.

### `expedition_spoils`

Captures returned spoils and recovered assets:

- `item_name`
- `quantity`
- `unit_value_estimate`
- `category`: one of `Units`, `Nanites`, `Trade Good`, `Module`, `Artifact`, `Material`, or `Other`.
- `notes`

Items categorized as `Units` are converted directly into wallet currency.
Other categories are added to inventory.

### `unit_ledger`

Maintains financial transaction history:

- `transaction_type`: `Income`, `Expense`, `Investment`, or `Balance Set`.
- `amount_units`
- `source_category`
- `description`
- optional `expedition_id` linkage.

The ledger is used for financial summaries, balance tracking, and auditability.

### `inventory_manifest`

Tracks physical cargo and acquired items:

- `item_name`
- `category`
- `quantity`
- `unit_value_estimate`
- `storage_location` (default `Freighter`)
- `last_updated`
- `notes`

This table supports inventory manifests for recovered modules, materials, artifacts, and trade goods.

### `player_state`

Single-row state information for the operator:

- `current_balance_units`
- `traveler_standing`
- `last_updated`
- `initial_balance_set`

Only one row is permitted, ensuring a single authoritative wallet state.

## Core Workflow

The fleet manager is driven through a menu-based interface with clearly defined operations.
Each command maps to business logic in `FleetLogistics`.

### Main Menu Operations

The interface exposes the following options:

- `[1] Recruit Frigate`
- `[2] View Fleet Registry`
- `[3] Launch Expedition`
- `[4] Record Expedition Spoils`
- `[5] Expedition History`
- `[6] Financial Summary`
- `[7] Inventory Manifest`
- `[8] Record Transaction`
- `[9] Export Data (CSV)`
- `[R] Reconcile Balance`
- `[0] Terminate Session`

### Balance Display

Before each menu display, the system shows the current wallet balance with a convergence status indicator:

- `MAXIMUM CONVERGENCE`
- `PROSPEROUS`
- `ADEQUATE`
- `MODEST`
- `MINIMAL`
- `DEPLETED`

This provides immediate operational context on financial health.

## Detailed Feature Behavior

### Frigate Recruitment

Recruitment is handled through `recruit_frigate(name, frigate_class, tier, cost, specialization, notes)`.

- Validates that the frigate designation is unique.
- Verifies sufficient wallet balance.
- Inserts the frigate into `fleet_registry`.
- Deducts recruitment cost from the wallet.
- Records an `Investment` transaction in `unit_ledger`.
- Reports success and updated balance.

### Fleet Registry Viewing

The fleet registry can be filtered by class and status.
The system displays:

- total registered vessels
- active and damaged counts
- total recruitment investment
- each vessel's tier, name, class, and cost

### Expedition Launch

Expedition launches are recorded through `launch_expedition(expedition_type, duration_hours, fuel_cost, frigate_ids)`.

Key checks include:

- at least one frigate selected
- fuel cost affordability
- all selected vessels are `Active`

On success:

- creates an expedition record
- links each deployed frigate
- deducts fuel cost from wallet
- records an `Expense` transaction
- reports expected return date

### Expedition Spoils Recording

When an expedition returns, spoils are catalogued using `record_expedition_spoils(expedition_id, spoils_list, result)`.

For each spoil item:

- stores it in `expedition_spoils`
- converts `Units` category spoils directly into wallet balance
- updates `inventory_manifest` for non-unit items
- logs expedition result and reports totals

### Expedition History

The history view summarizes recent expeditions, including:

- expedition date
- mission type
- duration
- fuel cost
- net position (spoils value minus fuel)
- mission result iconography

A configurable number of recent expeditions can be displayed.

### Financial Summary

The financial summary aggregates ledger and fleet metrics:

- wallet balance
- initial balance set
- total income
- expedition payouts
- fleet investment
- operational expenses
- fleet size and value
- expedition count and success rate
- total fuel burned

A warning is shown if balance is low.

### Inventory Manifest

Inventory can be listed by category or shown in full.
The manifest report includes:

- item category headings
- quantity
- estimated unit value
- cumulative estimated value

Inventory items are updated when spoils are recorded or manually added.

### Manual Transaction Recording

Operators may manually record:

- `Income` entries: add units to the wallet
- `Expense` entries: deduct units from the wallet

Each manual transaction is recorded in `unit_ledger`.

### Balance Reconciliation

If the recorded wallet differs from actual in-game inventory, reconciliation allows manual override.

- `force_set_balance(amount)` updates the wallet and records a `Balance Set` transaction.
- Large discrepancies trigger an audit warning.

### Export to CSV

Two export paths are available:

- `fleet_manifest.csv`: exports current fleet registry
- `expedition_log.csv`: exports expedition history and net profit calculations

Exports support external analysis and reporting.

## Deployment and Persistence

- Database file: `korvax_fleet.db`
- Auto-created on first execution
- Local SQLite storage ensures portability and simplicity
- Removing the database resets all recorded fleet state

## Operational Notes

- All numeric values are expected as integers, except expedition duration, which supports floating-point hours.
- All entered data is subject to schema constraints.
- The interface is intentionally austere to reflect Convergence Logistics Company's focus on efficiency.
- This is a single-user, session-driven tool. It does not provide networked multi-user concurrency.

## Development Notes

The codebase is structured for clarity and extensibility:

- `FleetDatabase` encapsulates schema and low-level SQLite access.
- `FleetLogistics` implements business operations and internal validation.
- `KorvaxInterface` renders prompts, menus, and output styling.

The application can be extended with additional validation, reporting, or export formats without disrupting the core persistence model.

## Conclusion

`nms_fleet.py` is the Convergence Logistics Company's fleet manager. It is a command-line operational tool designed to maintain fleet coherence, financial accuracy, expedition accountability, and inventory transparency.

Use it to keep your fleet aligned with Korvax logistics doctrine, and to ensure that every unit and every mission is recorded with precision.
