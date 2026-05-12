#!/usr/bin/env python3
"""
CONVERGENCE LOGISTICS COMPANY v1.0.6
==============================
Convergence-grade asset tracking for Traveler of the Atlas standing.
Tracks units on hand, frigates, expeditions, and spoils with computational precision.
Data integrity maintained. Regret is illogical.

Launch with: python nms_fleet.py
"""

import sqlite3
import csv
import os
from datetime import datetime, timedelta

# ============================================================
# KORVAX TERMINAL OUTPUT STYLING
# ============================================================

class KorvaxTerminal:
    """Renders outputs with appropriate Korvax computational aesthetic."""
    
    HEADER = "╔══════════════════════════════════════════════════════════════╗"
    FOOTER = "╚═════════════════════════════════════════════════════════════╝"
    DIVIDER = "╠═════════════════════════════════════════════════════════════╣"
    THIN = "──────────────────────────────────────────────────────────────"
    
    @staticmethod
    def title(text):
        print(f"\n{KorvaxTerminal.HEADER}")
        print(f"║  ◈ {text:<56}║")
        print(f"{KorvaxTerminal.DIVIDER}")
    
    @staticmethod
    def end_block():
        print(KorvaxTerminal.FOOTER)
    
    @staticmethod
    def info(label, value):
        print(f"║  ▸ {label:<20} {str(value):<32}║")
    
    @staticmethod
    def warn(text):
        print(f"\n  ◈ KORVAX ADVISORY: {text}")
    
    @staticmethod
    def error(text):
        print(f"\n  ◈ ANOMALY DETECTED: {text}")
    
    @staticmethod
    def success(text):
        print(f"\n  ◈ CONVERGENCE ACHIEVED: {text}")
    
    @staticmethod
    def prompt(text):
        return input(f"\n  ◈ {text} > ")


# ============================================================
# DATABASE CONVERGENCE
# ============================================================

class FleetDatabase:
    """SQLite convergence for all logistical entities."""
    
    def __init__(self, db_path="korvax_fleet.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Create tables if they do not exist. Existence is binary. Doubt is illogical."""
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS fleet_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frigate_name TEXT NOT NULL UNIQUE,
                frigate_class TEXT NOT NULL CHECK(frigate_class IN 
                    ('Combat','Trade','Exploration','Industrial','Support','Living')),
                tier TEXT NOT NULL CHECK(tier IN ('C','B','A','S')),
                recruitment_cost_units INTEGER NOT NULL,
                recruitment_date TEXT NOT NULL DEFAULT (date('now')),
                specialization TEXT,
                notes TEXT,
                active_status TEXT DEFAULT 'Active' CHECK(active_status IN 
                    ('Active','Damaged','Lost','Retired'))
            );
            
            CREATE TABLE IF NOT EXISTS expedition_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expedition_date TEXT NOT NULL DEFAULT (date('now')),
                expedition_type TEXT NOT NULL CHECK(expedition_type IN
                    ('Combat','Trade','Exploration','Industrial','Balanced')),
                duration_hours REAL NOT NULL,
                fuel_used_tonnes INTEGER NOT NULL,
                frigates_deployed INTEGER NOT NULL,
                expedition_result TEXT CHECK(expedition_result IN
                    ('Success','Partial','Failure','Frigate Damaged')),
                notes TEXT
            );
            
            CREATE TABLE IF NOT EXISTS expedition_frigate_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expedition_id INTEGER NOT NULL,
                frigate_id INTEGER NOT NULL,
                FOREIGN KEY(expedition_id) REFERENCES expedition_log(id) ON DELETE CASCADE,
                FOREIGN KEY(frigate_id) REFERENCES fleet_registry(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS expedition_spoils (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expedition_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                category TEXT CHECK(category IN
                    ('Units','Nanites','Trade Good','Module','Artifact','Material','Other')),
                notes TEXT,
                FOREIGN KEY(expedition_id) REFERENCES expedition_log(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS unit_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL DEFAULT (datetime('now')),
                transaction_type TEXT NOT NULL CHECK(transaction_type IN
                    ('Income','Expense','Investment','Balance Set')),
                amount_units INTEGER NOT NULL,
                source_category TEXT NOT NULL,
                description TEXT,
                expedition_id INTEGER,
                FOREIGN KEY(expedition_id) REFERENCES expedition_log(id) ON DELETE SET NULL
            );
            
            CREATE TABLE IF NOT EXISTS inventory_manifest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                storage_location TEXT DEFAULT 'Freighter',
                last_updated TEXT NOT NULL DEFAULT (datetime('now')),
                notes TEXT
            );
            
            CREATE TABLE IF NOT EXISTS player_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),  -- Only one row allowed
                current_balance_units INTEGER NOT NULL DEFAULT 0,
                current_fuel_tonnes INTEGER NOT NULL DEFAULT 0,
                traveler_standing TEXT DEFAULT 'Traveler of the Atlas',
                last_updated TEXT NOT NULL DEFAULT (datetime('now')),
                initial_balance_set INTEGER NOT NULL DEFAULT 0
            );
        """)
        
        # Ensure player_state has the singleton row
        self.cursor.execute("""
            INSERT OR IGNORE INTO player_state (id, current_balance_units, current_fuel_tonnes, traveler_standing)
            VALUES (1, 0, 0, 'Traveler of the Atlas')
        """)
        
        self.conn.commit()
        self._migrate_schema()
    
    def _migrate_schema(self):
        """Migrate legacy database schema to support fuel tracking."""
        player_columns = [row['name'] for row in self.cursor.execute("PRAGMA table_info(player_state)").fetchall()]
        if 'current_fuel_tonnes' not in player_columns:
            self.cursor.execute(
                "ALTER TABLE player_state ADD COLUMN current_fuel_tonnes INTEGER NOT NULL DEFAULT 0"
            )
        expedition_columns = [row['name'] for row in self.cursor.execute("PRAGMA table_info(expedition_log)").fetchall()]
        if 'fuel_used_tonnes' not in expedition_columns:
            self.cursor.execute(
                "ALTER TABLE expedition_log ADD COLUMN fuel_used_tonnes INTEGER NOT NULL DEFAULT 0"
            )
            if 'fuel_cost_units' in expedition_columns:
                self.cursor.execute(
                    "UPDATE expedition_log SET fuel_used_tonnes = fuel_cost_units"
                )
        
        # Remove unit_value_estimate from expedition_spoils if it exists
        spoils_columns = [row['name'] for row in self.cursor.execute("PRAGMA table_info(expedition_spoils)").fetchall()]
        if 'unit_value_estimate' in spoils_columns:
            self._recreate_table_without_column('expedition_spoils', 'unit_value_estimate')
        
        # Remove unit_value_estimate from inventory_manifest if it exists
        inventory_columns = [row['name'] for row in self.cursor.execute("PRAGMA table_info(inventory_manifest)").fetchall()]
        if 'unit_value_estimate' in inventory_columns:
            self._recreate_table_without_column('inventory_manifest', 'unit_value_estimate')
        
        self.conn.commit()
    
    def _recreate_table_without_column(self, table_name, column_to_remove):
        """Recreate a table without a specific column, preserving data."""
        # Get current schema
        schema = self.cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = [col['name'] for col in schema if col['name'] != column_to_remove]
        
        # Create new table without the column
        if table_name == 'expedition_spoils':
            self.cursor.execute(f"""
                CREATE TABLE {table_name}_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expedition_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    category TEXT CHECK(category IN
                        ('Units','Nanites','Trade Good','Module','Artifact','Material','Other')),
                    notes TEXT,
                    FOREIGN KEY(expedition_id) REFERENCES expedition_log(id) ON DELETE CASCADE
                )
            """)
        elif table_name == 'inventory_manifest':
            self.cursor.execute(f"""
                CREATE TABLE {table_name}_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    storage_location TEXT DEFAULT 'Freighter',
                    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
                    notes TEXT
                )
            """)
        
        # Copy data
        columns_str = ', '.join(columns)
        self.cursor.execute(f"INSERT INTO {table_name}_new ({columns_str}) SELECT {columns_str} FROM {table_name}")
        
        # Drop old table and rename new one
        self.cursor.execute(f"DROP TABLE {table_name}")
        self.cursor.execute(f"ALTER TABLE {table_name}_new RENAME TO {table_name}")

    def get_current_balance(self):
        """Retrieve the player's current unit balance."""
        result = self.cursor.execute(
            "SELECT current_balance_units, initial_balance_set FROM player_state WHERE id = 1"
        ).fetchone()
        return result['current_balance_units'], bool(result['initial_balance_set'])

    def get_current_fuel(self):
        """Retrieve the current frigate fuel reserve in tonnes."""
        result = self.cursor.execute(
            "SELECT current_fuel_tonnes FROM player_state WHERE id = 1"
        ).fetchone()
        return result['current_fuel_tonnes']

    def update_fuel(self, delta):
        """Adjust the frigate fuel reserve and return the new total."""
        current = self.get_current_fuel()
        new_fuel = current + delta
        if new_fuel < 0:
            KorvaxTerminal.error(
                f"Insufficient fuel. Available: {current:,}t | Required: {abs(delta):,}t"
            )
            return None
        self.cursor.execute(
            "UPDATE player_state SET current_fuel_tonnes = ?, last_updated = datetime('now') WHERE id = 1",
            (new_fuel,)
        )
        self.conn.commit()
        return new_fuel
    
    def set_initial_balance(self, amount):
        """Set the starting balance. Only works once unless forced."""
        current, already_set = self.get_current_balance()
        
        if not already_set:
            self.cursor.execute(
                "UPDATE player_state SET current_balance_units = ?, initial_balance_set = 1, last_updated = datetime('now')",
                (amount,)
            )
            self.cursor.execute(
                "INSERT INTO unit_ledger (transaction_date, transaction_type, amount_units, source_category, description) VALUES (datetime('now'), 'Balance Set', ?, 'Initialization', 'Traveler wallet initialized')",
                (amount,)
            )
            self.conn.commit()
            return True, amount
        else:
            return False, current
    
    def update_balance(self, delta):
        """
        Adjust the player balance by a delta (positive or negative).
        Returns the new balance. Refuses to go below zero unless override.
        """
        current, _ = self.get_current_balance()
        new_balance = current + delta
        
        if new_balance < 0:
            KorvaxTerminal.error(
                f"Insufficient units. Balance: {current:,} | Required: {abs(delta):,} | "
                f"Shortfall: {abs(new_balance):,}"
            )
            return None
        
        self.cursor.execute(
            "UPDATE player_state SET current_balance_units = ?, last_updated = datetime('now')",
            (new_balance,)
        )
        self.conn.commit()
        return new_balance
    
    def force_set_balance(self, amount):
        """Override the current balance with a new value. For reconciliation."""
        self.cursor.execute(
            "UPDATE player_state SET current_balance_units = ?, last_updated = datetime('now')",
            (amount,)
        )
        self.cursor.execute(
            "INSERT INTO unit_ledger (transaction_date, transaction_type, amount_units, source_category, description) VALUES (datetime('now'), 'Balance Set', ?, 'Reconciliation', 'Manual balance override')",
            (amount,)
        )
        self.conn.commit()
        return amount
    
    def execute(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        self.conn.commit()
        return self.cursor
    
    def fetch_all(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def fetch_one(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchone()
    
    def close(self):
        self.conn.close()


# ============================================================
# LOGISTICS OPERATIONS
# ============================================================

class FleetLogistics:
    """Primary operational interface. Computation without sentiment."""
    
    def __init__(self, db):
        self.db = db
    
    def display_balance(self):
        """Show current wallet balance prominently."""
        balance, initialized = self.db.get_current_balance()
        
        if not initialized:
            KorvaxTerminal.warn("Wallet not initialized. Use option [S] to set starting balance.")
            return None
        
        # Color-ish indicators via symbols
        if balance >= 1000000000:
            status = "◈ MAXIMUM CONVERGENCE"
        elif balance >= 100000000:
            status = "◉ PROSPEROUS"
        elif balance >= 10000000:
            status = "◎ ADEQUATE"
        elif balance >= 1000000:
            status = "◌ MODEST"
        elif balance > 0:
            status = "○ MINIMAL"
        else:
            status = "⊗ DEPLETED"
        
        print(f"\n  ◈ CURRENT UNITS ON HAND: {balance:,}  [{status}]")
        fuel = self.db.get_current_fuel()
        print(f"  ◈ CURRENT FRIGATE FUEL: {fuel:,} tonnes")
        return balance
    
    # --- FRIGATE MANAGEMENT ---
    
    def recruit_frigate(self, name, frigate_class, tier, cost, specialization="", notes=""):
        """Add a new frigate to fleet registry. Cost deducted from balance."""
        existing = self.db.fetch_one(
            "SELECT id FROM fleet_registry WHERE frigate_name = ?", (name,)
        )
        if existing:
            KorvaxTerminal.error(f"Frigate designation '{name}' already exists in registry.")
            return False
        
        # Check balance
        balance, _ = self.db.get_current_balance()
        if cost > balance:
            KorvaxTerminal.error(
                f"Insufficient units. Cost: {cost:,} | Balance: {balance:,} | "
                f"Shortfall: {cost - balance:,}"
            )
            return False
        
        self.db.execute("""
            INSERT INTO fleet_registry 
            (frigate_name, frigate_class, tier, recruitment_cost_units, specialization, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, frigate_class, tier, cost, specialization, notes))
        
        # Deduct from balance
        new_balance = self.db.update_balance(-cost)
        
        # Log the unit expenditure
        self._record_transaction(
            'Investment', cost, 'Frigate Recruitment', 
            f"Recruited {tier}-Class {frigate_class}: {name}"
        )
        
        KorvaxTerminal.success(
            f"Frigate '{name}' integrated into fleet registry. "
            f"{cost:,} units deducted. Balance: {new_balance:,}"
        )
        return True
    
    def view_fleet(self, filter_class=None, filter_status=None):
        """Display fleet registry with optional filtration parameters."""
        query = "SELECT * FROM fleet_registry"
        conditions = []
        params = []
        
        if filter_class:
            conditions.append("frigate_class = ?")
            params.append(filter_class)
        if filter_status:
            conditions.append("active_status = ?")
            params.append(filter_status)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY frigate_class, tier DESC, frigate_name"
        
        frigates = self.db.fetch_all(query, params)
        
        if not frigates:
            KorvaxTerminal.warn("No frigates found matching parameters. Fleet requires expansion.")
            return frigates
        
        total_cost = sum(f['recruitment_cost_units'] for f in frigates)
        active = sum(1 for f in frigates if f['active_status'] == 'Active')
        damaged = sum(1 for f in frigates if f['active_status'] == 'Damaged')
        
        KorvaxTerminal.title(f"FLEET REGISTRY [{len(frigates)} vessels]")
        KorvaxTerminal.info("Active Vessels", active)
        KorvaxTerminal.info("Damaged Vessels", damaged)
        KorvaxTerminal.info("Total Investment", f"{total_cost:,} units")
        print(f"║{KorvaxTerminal.THIN}║")
        
        for f in frigates:
            status_marker = "◉" if f['active_status'] == 'Active' else "◌"
            print(f"║  {status_marker} [{f['tier']}] {f['frigate_name']:<20} {f['frigate_class']:<12} {f['recruitment_cost_units']:>10,}u ║")
        
        KorvaxTerminal.end_block()
        return frigates
    
    # --- EXPEDITION MANAGEMENT ---
    
    def launch_expedition(self, expedition_type, duration_hours, fuel_tonnes, frigate_ids):
        """Log an expedition and assign frigates. Fuel tonnes are consumed from reserves."""
        if not frigate_ids:
            KorvaxTerminal.error("Expedition requires at least one frigate. Logic demands it.")
            return None
        
        # Check fuel reserves
        current_fuel = self.db.get_current_fuel()
        if fuel_tonnes <= 0:
            KorvaxTerminal.error("Fuel consumption must be a positive integer.")
            return None
        if fuel_tonnes > current_fuel:
            KorvaxTerminal.error(
                f"Insufficient fuel. Required: {fuel_tonnes:,}t | Available: {current_fuel:,}t"
            )
            return None
        
        # Verify all frigates exist and are active
        placeholders = ','.join('?' * len(frigate_ids))
        active_count = self.db.fetch_one(
            f"SELECT COUNT(*) as count FROM fleet_registry WHERE id IN ({placeholders}) AND active_status = 'Active'",
            frigate_ids
        )
        
        if active_count['count'] < len(frigate_ids):
            KorvaxTerminal.error("One or more selected frigates are unavailable. Check damage status.")
            return None
        
        expedition_id = self.db.execute("""
            INSERT INTO expedition_log 
            (expedition_date, expedition_type, duration_hours, fuel_used_tonnes, frigates_deployed, expedition_result)
            VALUES (date('now'), ?, ?, ?, ?, 'Success')
        """, (expedition_type, duration_hours, fuel_tonnes, len(frigate_ids))).lastrowid
        
        # Assign frigates
        for fid in frigate_ids:
            self.db.execute("""
                INSERT INTO expedition_frigate_assignments (expedition_id, frigate_id)
                VALUES (?, ?)
            """, (expedition_id, fid))
        
        new_fuel = self.db.update_fuel(-fuel_tonnes)
        return_date = datetime.now() + timedelta(hours=duration_hours)
        KorvaxTerminal.success(
            f"Expedition {expedition_id} launched. {len(frigate_ids)} frigates deployed. "
            f"Fuel consumed: {fuel_tonnes:,} tonnes | Fuel remaining: {new_fuel:,} tonnes\n"
            f"  Return expected: {return_date.strftime('%Y-%m-%d %H:%M')}"
        )
        return expedition_id
    
    def record_expedition_spoils(self, expedition_id, spoils_list, result="Success"):
        """
        Record spoils from a returned expedition.
        spoils_list: list of dicts with keys: item_name, quantity, category
        Unit-valued spoils are added directly to wallet balance.
        """
        # Update expedition result
        self.db.execute(
            "UPDATE expedition_log SET expedition_result = ? WHERE id = ?",
            (result, expedition_id)
        )
        
        total_units_earned = 0
        
        for spoil in spoils_list:
            self.db.execute("""
                INSERT INTO expedition_spoils 
                (expedition_id, item_name, quantity, category, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                expedition_id,
                spoil.get('item_name', 'Unknown Item'),
                spoil.get('quantity', 1),
                spoil.get('category', 'Other'),
                spoil.get('notes', '')
            ))
            
            # If the spoil category is "Units", add quantity directly to wallet balance
            if spoil.get('category') == 'Units':
                total_units_earned += spoil.get('quantity', 1)
            else:
                # Update inventory for physical items
                self._update_inventory(
                    spoil.get('item_name', 'Unknown Item'),
                    spoil.get('category', 'Other'),
                    spoil.get('quantity', 1)
                )
        
        # Add units directly to balance (not inventory)
        if total_units_earned > 0:
            new_balance = self.db.update_balance(total_units_earned)
            self._record_transaction(
                'Income', total_units_earned, 'Expedition Returns',
                f"Expedition {expedition_id} direct unit payout: {total_units_earned:,}u"
            )
        
        KorvaxTerminal.success(
            f"Expedition {expedition_id} concluded.\n"
            f"  Direct units earned: {total_units_earned:,}u\n"
            f"  Items added to inventory.\n"
            f"  Result: {result}"
        )
    
    def view_expedition_history(self, limit=10):
        """Display recent expedition log with spoils summary."""
        expeditions = self.db.fetch_all("""
            SELECT e.*, 
                   COUNT(es.id) as spoil_types,
                   SUM(CASE WHEN es.category = 'Units' THEN es.quantity ELSE 0 END) as direct_units,
                   0 as item_value
            FROM expedition_log e
            LEFT JOIN expedition_spoils es ON e.id = es.expedition_id
            GROUP BY e.id
            ORDER BY e.expedition_date DESC
            LIMIT ?
        """, (limit,))
        
        if not expeditions:
            KorvaxTerminal.warn("No expedition data available. Fleet lies dormant.")
            return
        
        KorvaxTerminal.title(f"EXPEDITION LOG [{len(expeditions)} recent]")
        
        total_net = 0
        for exp in expeditions:
            result_icon = {
                "Success": "◉", "Partial": "◌", 
                "Failure": "⊗", "Frigate Damaged": "⚠"
            }.get(exp['expedition_result'], '?')
            
            gross = (exp['direct_units'] or 0) + (exp['item_value'] or 0)
            net = gross
            total_net += net
            
            print(f"║  {result_icon} #{exp['id']:<4} {exp['expedition_date']} {exp['expedition_type']:<12} "
                  f"{exp['duration_hours']}h | Fuel:{exp['fuel_used_tonnes']:>6,}t → Net:{net:>8,}u ║")
        
        KorvaxTerminal.info("Total Net Position", f"{total_net:,} units")
        KorvaxTerminal.end_block()
    
    # --- FINANCIAL OPERATIONS ---
    
    def _record_transaction(self, trans_type, amount, category, description, expedition_id=None):
        """Internal: log a unit transaction."""
        self.db.execute("""
            INSERT INTO unit_ledger 
            (transaction_date, transaction_type, amount_units, source_category, description, expedition_id)
            VALUES (datetime('now'), ?, ?, ?, ?, ?)
        """, (trans_type, amount, category, description, expedition_id))
    
    def record_income(self, amount, source, description):
        """Log units earned from non-expedition sources. Adds to wallet."""
        new_balance = self.db.update_balance(amount)
        if new_balance is not None:
            self._record_transaction('Income', amount, source, description)
            KorvaxTerminal.success(f"{amount:,} units added. New balance: {new_balance:,}")
    
    def record_expense(self, amount, source, description):
        """Log unit expenditures. Deducts from wallet."""
        new_balance = self.db.update_balance(-amount)
        if new_balance is not None:
            self._record_transaction('Expense', amount, source, description)
            KorvaxTerminal.info(f"{amount:,} units expended. New balance: {new_balance:,}")

    def resupply_fuel(self, tonnes, unit_cost=0):
        """Add frigate fuel reserves in tonnes, optionally paying units if cost is provided."""
        if tonnes <= 0:
            KorvaxTerminal.error("Refuel amount must be a positive integer.")
            return None
        if unit_cost < 0:
            KorvaxTerminal.error("Unit cost cannot be negative.")
            return None
        if unit_cost and self.db.update_balance(-unit_cost) is None:
            return None
        if unit_cost:
            self._record_transaction(
                'Expense', unit_cost, 'Fuel Purchase',
                f"Purchased {tonnes:,} tonnes of frigate fuel"
            )
        new_fuel = self.db.update_fuel(tonnes)
        if new_fuel is not None:
            KorvaxTerminal.success(
                f"Refueled {tonnes:,} tonnes. Current fuel reserves: {new_fuel:,} tonnes."
            )
        return new_fuel
    
    def view_financial_summary(self):
        """Display unit ledger convergence - income, expenses, net position."""
        # Get wallet balance
        balance, initialized = self.db.get_current_balance()
        
        # Get transaction totals
        income = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount_units), 0) as total FROM unit_ledger WHERE transaction_type = 'Income'"
        )
        expenses = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount_units), 0) as total FROM unit_ledger WHERE transaction_type IN ('Expense', 'Investment')"
        )
        investments = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount_units), 0) as total FROM unit_ledger WHERE transaction_type = 'Investment'"
        )
        balance_sets = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount_units), 0) as total FROM unit_ledger WHERE transaction_type = 'Balance Set'"
        )
        
        # Fleet summary
        fleet_count = self.db.fetch_one("SELECT COUNT(*) as count FROM fleet_registry")['count']
        fleet_value = self.db.fetch_one(
            "SELECT COALESCE(SUM(recruitment_cost_units), 0) as total FROM fleet_registry"
        )['total']
        
        # Expedition stats
        exp_stats = self.db.fetch_one("""
            SELECT 
                COUNT(*) as total_expeditions,
                COALESCE(SUM(fuel_used_tonnes), 0) as total_fuel_burned,
                COALESCE(SUM(CASE WHEN expedition_result = 'Success' THEN 1 ELSE 0 END), 0) as successful
            FROM expedition_log
        """)
        
        total_spoil_value = self.db.fetch_one("""
            SELECT COALESCE(SUM(quantity), 0) as total
            FROM expedition_spoils WHERE category = 'Units'
        """)['total']
        
        KorvaxTerminal.title("UNIT LEDGER CONVERGENCE")
        KorvaxTerminal.info("WALLET BALANCE", f"{balance:,} units")
        print(f"║{KorvaxTerminal.THIN}║")
        KorvaxTerminal.info("Initial Balance Set", f"{balance_sets['total']:,} units")
        KorvaxTerminal.info("Total Income (non-spoil)", f"{income['total']:,} units")
        KorvaxTerminal.info("Expedition Payouts", f"{total_spoil_value:,} units")
        KorvaxTerminal.info("Fleet Investment", f"{investments['total']:,} units")
        KorvaxTerminal.info("Operational Expenses", f"{(expenses['total'] - investments['total']):,} units")
        print(f"║{KorvaxTerminal.THIN}║")
        KorvaxTerminal.info("Fleet Size", f"{fleet_count} vessels worth {fleet_value:,}u")
        KorvaxTerminal.info("Expeditions", f"{exp_stats['total_expeditions']} total, {exp_stats['successful']} successful")
        KorvaxTerminal.info("Total Fuel Burned", f"{exp_stats['total_fuel_burned']:,} tonnes")
        
        if balance < 100000:
            KorvaxTerminal.warn("Balance low. Consider trade route optimization or frigate deployment.")
        
        KorvaxTerminal.end_block()
    
    # --- INVENTORY MANAGEMENT ---
    
    def _update_inventory(self, item_name, category, quantity):
        """Add or update inventory item."""
        existing = self.db.fetch_one(
            "SELECT id, quantity FROM inventory_manifest WHERE item_name = ? AND category = ?",
            (item_name, category)
        )
        if existing:
            self.db.execute(
                "UPDATE inventory_manifest SET quantity = quantity + ?, last_updated = datetime('now') WHERE id = ?",
                (quantity, existing['id'])
            )
        else:
            self.db.execute(
                """INSERT INTO inventory_manifest 
                (item_name, category, quantity, last_updated)
                VALUES (?, ?, ?, datetime('now'))""",
                (item_name, category, quantity)
            )
    
    def add_inventory_item(self, item_name, category, quantity, location="Freighter"):
        """Manually add item to inventory manifest."""
        self._update_inventory(item_name, category, quantity)
        KorvaxTerminal.success(f"{quantity}x {item_name} added to {location} manifest.")
    
    def view_inventory(self, category_filter=None):
        """Display inventory manifest."""
        query = "SELECT * FROM inventory_manifest"
        params = []
        if category_filter:
            query += " WHERE category = ?"
            params.append(category_filter)
        query += " ORDER BY category, item_name"
        
        items = self.db.fetch_all(query, params)
        
        if not items:
            KorvaxTerminal.warn("Inventory manifest is empty. Acquisition required.")
            return
        
        total_value = 0  # No longer calculated since unit_value_estimate removed
        
        KorvaxTerminal.title(f"MANIFEST [{len(items)} item types]")
        
        current_category = ""
        for item in items:
            if item['category'] != current_category:
                current_category = item['category']
                print(f"║  ── {current_category} ──{' ' * (52 - len(current_category))}║")
            print(f"║    {item['quantity']:>4}x {item['item_name']:<30} ║")
        
        KorvaxTerminal.end_block()
    
    # --- BALANCE MANAGEMENT ---
    
    def initialize_wallet(self, amount):
        """Set the starting balance. Can only be done once."""
        success, current = self.db.set_initial_balance(amount)
        if success:
            KorvaxTerminal.success(f"Wallet initialized with {amount:,} units.")
            KorvaxTerminal.info("Traveler standing", "Traveler of the Atlas")
            return True
        else:
            KorvaxTerminal.error(
                f"Wallet already initialized with {current:,} units. "
                f"Use reconciliation (option [R]) to override."
            )
            return False
    
    def reconcile_balance(self, amount):
        """Force-set balance to match actual in-game wallet."""
        old_balance, _ = self.db.get_current_balance()
        new_balance = self.db.force_set_balance(amount)
        difference = amount - old_balance
        
        KorvaxTerminal.success(
            f"Balance reconciled: {old_balance:,} → {new_balance:,} "
            f"({'+' if difference >= 0 else ''}{difference:,} units adjustment)"
        )
        if abs(difference) > 1000000:
            KorvaxTerminal.warn(
                f"Large discrepancy detected ({difference:,}u). "
                "Verify expedition logs for unrecorded activity."
            )
    
    # --- EXPORT OPERATIONS ---
    
    def export_fleet_to_csv(self, filename="fleet_manifest.csv"):
        """Export fleet registry to CSV for external convergence."""
        frigates = self.db.fetch_all("SELECT * FROM fleet_registry ORDER BY frigate_class, tier")
        if not frigates:
            KorvaxTerminal.error("No data to export.")
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Class', 'Tier', 'Cost', 'Specialization', 'Status', 'Recruited'])
            for frig in frigates:
                writer.writerow([
                    frig['frigate_name'], frig['frigate_class'], frig['tier'],
                    frig['recruitment_cost_units'], frig['specialization'],
                    frig['active_status'], frig['recruitment_date']
                ])
        
        KorvaxTerminal.success(f"Fleet registry exported to {filename}")
    
    def export_expeditions_to_csv(self, filename="expedition_log.csv"):
        """Export expedition data for external analysis."""
        expeditions = self.db.fetch_all("""
            SELECT e.id, e.expedition_date, e.expedition_type, e.duration_hours,
                   e.fuel_used_tonnes, e.expedition_result, e.frigates_deployed,
                   COUNT(es.id) as spoil_count,
                   COALESCE(SUM(CASE WHEN es.category = 'Units' THEN es.quantity ELSE 0 END), 0) as unit_spoils
            FROM expedition_log e
            LEFT JOIN expedition_spoils es ON e.id = es.expedition_id
            GROUP BY e.id
            ORDER BY e.expedition_date DESC
        """)
        
        if not expeditions:
            KorvaxTerminal.error("No expedition data to export.")
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Date', 'Type', 'Hours', 'Fuel Tonnes', 'Result', 
                            'Frigates', 'Spoil Types', 'Unit Spoils', 'Net Profit'])
            for exp in expeditions:
                net = exp['unit_spoils'] or 0
                writer.writerow([
                    exp['id'], exp['expedition_date'], exp['expedition_type'],
                    exp['duration_hours'], exp['fuel_used_tonnes'], exp['expedition_result'],
                    exp['frigates_deployed'], exp['spoil_count'], exp['unit_spoils'] or 0, net
                ])
        
        KorvaxTerminal.success(f"Expedition log exported to {filename}")


# ============================================================
# TERMINAL INTERFACE
# ============================================================

class KorvaxInterface:
    """Primary interaction layer. Efficient. Logical. Minimal small talk."""
    
    def __init__(self):
        self.db = FleetDatabase()
        self.logistics = FleetLogistics(self.db)
        os.system('title "Convergence Logistics Company"')
        self._check_initialization()
    
    def _check_initialization(self):
        """Check if wallet is set up. Prompt if not."""
        balance, initialized = self.db.get_current_balance()
        if not initialized:
            print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ◈  FIRST CONVERGENCE DETECTED  ◈                        ║
║                                                              ║
║     Before fleet operations can commence, the system         ║
║     requires your current unit balance.                      ║
║                                                              ║
║     Enter the units currently in your exosuit.               ║
║     Accuracy is logical. Deception is... unwise.             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
            """)
            while True:
                try:
                    amount = int(KorvaxTerminal.prompt("Current unit balance"))
                    if amount < 0:
                        KorvaxTerminal.error("Negative balance illogical. Enter positive integer.")
                        continue
                    self.logistics.initialize_wallet(amount)
                    break
                except ValueError:
                    KorvaxTerminal.error("Integer value required. Units are whole numbers.")
    
    def run(self):
        """Initialize convergence loop."""
        self._display_splash()
        
        while True:
            self.logistics.display_balance()
            self._display_menu()
            choice = KorvaxTerminal.prompt("Select operation").upper()
            
            if choice == '1':
                self._menu_recruit_frigate()
            elif choice == '2':
                self._menu_view_fleet()
            elif choice == '3':
                self._menu_launch_expedition()
            elif choice == '4':
                self._menu_record_spoils()
            elif choice == '5':
                self._menu_view_expeditions()
            elif choice == '6':
                self._menu_finances()
            elif choice == '7':
                self._menu_inventory()
            elif choice == 'F':
                self._menu_refuel_fleet()
            elif choice == '8':
                self._menu_record_transaction()
            elif choice == '9':
                self._menu_export()
            elif choice == 'R':
                self._menu_reconcile()
            elif choice == '0':
                self._shutdown()
                break
            else:
                KorvaxTerminal.error("Invalid input. Acceptable: 0-9, R, S.")
    
    def _display_splash(self):
        print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ◈  CONVERGENCE LOGISTICS COMPANY  ◈                     ║
║                                                              ║
║     Convergence-grade fleet asset management                 ║
║     for Traveler of the Atlas standing                       ║
║                                                              ║
║     All transactions affect wallet balance.                  ║
║     All probabilities calculated.                            ║
║     Sentiment: irrelevant. Efficiency: paramount.            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def _display_menu(self):
        print(f"""
{KorvaxTerminal.DIVIDER}
║  OPERATIONS MENU                                            ║
{KorvaxTerminal.DIVIDER}
║  [1] Recruit Frigate         [6] Financial Summary          ║
║  [2] View Fleet Registry     [7] Inventory Manifest         ║
║  [3] Launch Expedition       [8] Record Transaction         ║
║  [4] Record Expedition Spoils[9] Export Data (CSV)          ║
║  [5] Expedition History      [F] Refuel Supply             ║
║                              [R] Reconcile Balance          ║
║                              [0] Terminate Session          ║
{KorvaxTerminal.FOOTER}
        """)
    
    def _menu_recruit_frigate(self):
        KorvaxTerminal.title("FRIGATE RECRUITMENT PROTOCOL")
        name = KorvaxTerminal.prompt("Frigate designation")
        if not name:
            return
        
        print("\n  Classes: Combat | Trade | Exploration | Industrial | Support | Living")
        f_class = KorvaxTerminal.prompt("Frigate class")
        if f_class not in ['Combat','Trade','Exploration','Industrial','Support','Living']:
            KorvaxTerminal.error("Invalid class designation.")
            return
        
        tier = KorvaxTerminal.prompt("Tier (C/B/A/S)").upper()
        if tier not in ['C','B','A','S']:
            KorvaxTerminal.error("Invalid tier. Acceptable: C, B, A, S.")
            return
        
        try:
            cost = int(KorvaxTerminal.prompt("Recruitment cost (units)"))
        except ValueError:
            KorvaxTerminal.error("Cost must be integer value.")
            return
        
        spec = KorvaxTerminal.prompt("Specialization (optional)")
        notes = KorvaxTerminal.prompt("Operational notes (optional)")
        
        self.logistics.recruit_frigate(name, f_class, tier, cost, spec, notes)
    
    def _menu_view_fleet(self):
        print("\n  Filter options (press Enter to skip):")
        print("  Classes: Combat | Trade | Exploration | Industrial | Support | Living")
        f_class = KorvaxTerminal.prompt("Filter by class (or Enter for all)")
        print("  Status: Active | Damaged | Lost | Retired")
        f_status = KorvaxTerminal.prompt("Filter by status (or Enter for all)")
        
        self.logistics.view_fleet(
            filter_class=f_class if f_class else None,
            filter_status=f_status if f_status else None
        )
    
    def _menu_launch_expedition(self):
        KorvaxTerminal.title("EXPEDITION LAUNCH SEQUENCE")
        
        print("  Types: Combat | Trade | Exploration | Industrial | Balanced")
        exp_type = KorvaxTerminal.prompt("Expedition type")
        if exp_type not in ['Combat','Trade','Exploration','Industrial','Balanced']:
            KorvaxTerminal.error("Invalid expedition type.")
            return
        
        try:
            duration = float(KorvaxTerminal.prompt("Duration (hours)"))
            fuel = int(KorvaxTerminal.prompt("Fuel required (tonnes)"))
        except ValueError:
            KorvaxTerminal.error("Numeric values required.")
            return
        
        # Show available frigates
        available = self.db.fetch_all(
            "SELECT id, frigate_name, frigate_class, tier FROM fleet_registry WHERE active_status = 'Active'"
        )
        if not available:
            KorvaxTerminal.error("No active frigates available for deployment.")
            return
        
        print(f"\n  Available Frigates ({len(available)}):")
        for f in available:
            print(f"    ID:{f['id']:<3} [{f['tier']}] {f['frigate_name']:<20} ({f['frigate_class']})")
        
        ids_input = KorvaxTerminal.prompt("Frigate IDs to deploy (comma-separated)")
        try:
            frigate_ids = [int(x.strip()) for x in ids_input.split(',')]
        except ValueError:
            KorvaxTerminal.error("Invalid ID format.")
            return
        
        self.logistics.launch_expedition(exp_type, duration, fuel, frigate_ids)
    
    def _menu_refuel_fleet(self):
        KorvaxTerminal.title("FRIGATE FUEL RESUPPLY")
        try:
            tonnes = int(KorvaxTerminal.prompt("Fuel to add (tonnes)"))
            cost = int(KorvaxTerminal.prompt("Optional unit cost for this fuel purchase (0 if none)"))
        except ValueError:
            KorvaxTerminal.error("Numeric values required.")
            return
        self.logistics.resupply_fuel(tonnes, cost)

    def _menu_record_spoils(self):
        KorvaxTerminal.title("EXPEDITION SPOILS CATALOGUE")
        
        try:
            exp_id = int(KorvaxTerminal.prompt("Expedition ID"))
        except ValueError:
            KorvaxTerminal.error("Valid expedition ID required.")
            return
        
        # Verify expedition exists
        exp = self.db.fetch_one("SELECT * FROM expedition_log WHERE id = ?", (exp_id,))
        if not exp:
            KorvaxTerminal.error(f"Expedition {exp_id} not found in log.")
            return
        
        print(f"\n  Recording spoils for Expedition {exp_id} ({exp['expedition_type']})")
        print("  Categories: Units | Nanites | Trade Good | Module | Artifact | Material | Other")
        print("  ◈ NOTE: Items logged as 'Units' will be added directly to wallet balance.")
        
        spoils = []
        while True:
            print(f"\n  --- Spoil #{len(spoils) + 1} (Enter to finish) ---")
            item = KorvaxTerminal.prompt("Item name (or Enter to finish)")
            if not item:
                break
            
            try:
                qty = int(KorvaxTerminal.prompt("Quantity") or "1")
            except ValueError:
                KorvaxTerminal.error("Numeric values required.")
                continue
            
            cat = KorvaxTerminal.prompt("Category") or "Other"
            note = KorvaxTerminal.prompt("Notes (optional)")
            
            spoils.append({
                'item_name': item,
                'quantity': qty,
                'category': cat,
                'notes': note
            })
        
        if spoils:
            print("\n  Result: Success | Partial | Failure | Frigate Damaged")
            result = KorvaxTerminal.prompt("Expedition result") or "Success"
            self.logistics.record_expedition_spoils(exp_id, spoils, result)
        else:
            KorvaxTerminal.warn("No spoils recorded. Expedition log unchanged.")
    
    def _menu_view_expeditions(self):
        try:
            limit = int(KorvaxTerminal.prompt("Number of recent expeditions to display") or "10")
        except ValueError:
            limit = 10
        self.logistics.view_expedition_history(limit)
    
    def _menu_finances(self):
        self.logistics.view_financial_summary()
    
    def _menu_inventory(self):
        print("\n  Filter categories: Trade Good | Module | Artifact | Material | Other")
        cat = KorvaxTerminal.prompt("Filter by category (or Enter for all)")
        self.logistics.view_inventory(category_filter=cat if cat else None)
    
    def _menu_record_transaction(self):
        print("\n  Types: Income (adds to wallet) | Expense (deducts from wallet)")
        t_type = KorvaxTerminal.prompt("Transaction type")
        if t_type not in ['Income', 'Expense']:
            KorvaxTerminal.error("Invalid type.")
            return
        
        try:
            amount = int(KorvaxTerminal.prompt("Amount (units)"))
            if amount <= 0:
                KorvaxTerminal.error("Amount must be positive.")
                return
        except ValueError:
            KorvaxTerminal.error("Integer value required.")
            return
        
        source = KorvaxTerminal.prompt("Source/Category") or "Manual Entry"
        desc = KorvaxTerminal.prompt("Description (optional)")
        
        if t_type == 'Income':
            self.logistics.record_income(amount, source, desc)
        else:
            self.logistics.record_expense(amount, source, desc)
    
    def _menu_export(self):
        print("\n  [1] Export Fleet Registry CSV")
        print("  [2] Export Expedition Log CSV")
        choice = KorvaxTerminal.prompt("Select export")
        
        if choice == '1':
            filename = KorvaxTerminal.prompt("Filename") or "fleet_manifest.csv"
            self.logistics.export_fleet_to_csv(filename)
        elif choice == '2':
            filename = KorvaxTerminal.prompt("Filename") or "expedition_log.csv"
            self.logistics.export_expeditions_to_csv(filename)
    
    def _menu_reconcile(self):
        """Manually update wallet balance to match in-game value."""
        balance, _ = self.db.get_current_balance()
        KorvaxTerminal.title("BALANCE RECONCILIATION")
        KorvaxTerminal.info("Current Recorded Balance", f"{balance:,} units")
        print(f"║{KorvaxTerminal.THIN}║")
        KorvaxTerminal.warn("Use this if the Nexus balance differs from your in-game wallet.")
        
        try:
            new_balance = int(KorvaxTerminal.prompt("Actual in-game balance"))
            if new_balance < 0:
                KorvaxTerminal.error("Balance cannot be negative.")
                return
        except ValueError:
            KorvaxTerminal.error("Integer value required.")
            return
        
        self.logistics.reconcile_balance(new_balance)
    
    def _shutdown(self):
        balance, _ = self.db.get_current_balance()
        print(f"""
{KorvaxTerminal.HEADER}
║                                                              ║
║     Convergence complete.                                    ║
║     Final balance: {balance:>10,} units                      ║
║     All data preserved. All decisions logged.                ║
║     The Atlas sees your dedication to logistical purity.     ║
║                                                              ║
║     GRAH. (That is 'goodbye' in your parlance.)              ║
║                                                              ║
{KorvaxTerminal.FOOTER}
        """)
        self.db.close()


# ============================================================
# CONVERGENCE INITIATION
# ============================================================

if __name__ == "__main__":
    interface = KorvaxInterface()
    interface.run()