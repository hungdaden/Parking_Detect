"""
Backward compatibility module for db_manager.
Re-exports ParkingDB from the data layer (data.db_manager).
"""
from data.db_manager import ParkingDB

__all__ = ["ParkingDB"]
