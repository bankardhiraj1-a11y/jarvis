#!/usr/bin/env python3
"""
Reset database - Remove all test trades and metrics
Keeps only LIVE trading data going forward
"""

from database import SessionLocal, engine, Base
from models import Trade, Position, AgentMetrics
import sys

def reset_database():
    """Clear all test trades and reset to clean slate"""

    try:
        db = SessionLocal()

        # Count before reset
        trades_count = db.query(Trade).count()
        metrics_count = db.query(AgentMetrics).count()
        positions_count = db.query(Position).count()

        print("Database State:")
        print(f"   Trades: {trades_count}")
        print(f"   Metrics: {metrics_count}")
        print(f"   Positions: {positions_count}")
        print("")

        # Confirm deletion
        if trades_count > 0 or metrics_count > 0 or positions_count > 0:
            response = input("Delete all trades & metrics? (yes/no): ").strip().lower()

            if response != "yes":
                print("[CANCELLED] No changes made.")
                return

            # Delete all records
            db.query(Trade).delete()
            db.query(AgentMetrics).delete()
            db.query(Position).delete()
            db.commit()

            print("[SUCCESS] Database cleaned!")
            print("   - All test trades removed")
            print("   - All metrics reset")
            print("   - Ready for LIVE trading only")
        else:
            print("[OK] Database already clean!")

        db.close()

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database()
