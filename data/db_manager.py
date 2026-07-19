import sqlite3
import uuid
import os
from datetime import datetime


class ParkingDB:
    def __init__(self, db_path=None):
        if db_path is None:
            # Place DB next to workspace root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "parking.db")
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS parking_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL,
                vehicle_id TEXT,
                event_type TEXT NOT NULL,
                timestamp TEXT DEFAULT (datetime('now', 'localtime')),
                preset_name TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS slot_status (
                slot_id INTEGER PRIMARY KEY,
                is_occupied INTEGER DEFAULT 0,
                vehicle_id TEXT,
                last_updated TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS license_plates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_text TEXT NOT NULL,
                plate_image BLOB,
                timestamp TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()
        conn.close()

    def _gen_vehicle_id(self):
        return "V-" + uuid.uuid4().hex[:4]

    def record_vehicle_in(self, slot_id, preset_name=""):
        conn = self._get_conn()
        c = conn.cursor()
        vid = self._gen_vehicle_id()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO parking_events (slot_id, vehicle_id, event_type, timestamp, preset_name) VALUES (?, ?, 'IN', ?, ?)",
            (slot_id, vid, now, preset_name)
        )
        c.execute(
            "INSERT OR REPLACE INTO slot_status (slot_id, is_occupied, vehicle_id, last_updated) VALUES (?, 1, ?, ?)",
            (slot_id, vid, now)
        )
        conn.commit()
        conn.close()
        return vid

    def record_vehicle_out(self, slot_id, preset_name=""):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT vehicle_id FROM slot_status WHERE slot_id = ? AND is_occupied = 1", (slot_id,))
        row = c.fetchone()
        vid = row["vehicle_id"] if row else "unknown"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO parking_events (slot_id, vehicle_id, event_type, timestamp, preset_name) VALUES (?, ?, 'OUT', ?, ?)",
            (slot_id, vid, now, preset_name)
        )
        c.execute(
            "INSERT OR REPLACE INTO slot_status (slot_id, is_occupied, vehicle_id, last_updated) VALUES (?, 0, NULL, ?)",
            (slot_id, now)
        )
        conn.commit()
        conn.close()

    def get_today_stats(self):
        conn = self._get_conn()
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) as cnt FROM parking_events WHERE event_type='IN' AND timestamp LIKE ?", (today + "%",))
        total_in = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM parking_events WHERE event_type='OUT' AND timestamp LIKE ?", (today + "%",))
        total_out = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM slot_status WHERE is_occupied = 1")
        currently_occupied = c.fetchone()["cnt"]
        conn.close()
        return {
            "total_in": total_in,
            "total_out": total_out,
            "currently_occupied": currently_occupied
        }

    def get_history(self, limit=20):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM parking_events ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_slot_summary(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT slot_id, 
                   SUM(CASE WHEN event_type='IN' THEN 1 ELSE 0 END) as total_in,
                   SUM(CASE WHEN event_type='OUT' THEN 1 ELSE 0 END) as total_out
            FROM parking_events
            GROUP BY slot_id
            ORDER BY slot_id
        """)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def reset_slot_status(self, total_slots):
        """Reset toàn bộ slot_status khi bắt đầu session mới"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM slot_status")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for i in range(1, total_slots + 1):
            c.execute(
                "INSERT INTO slot_status (slot_id, is_occupied, vehicle_id, last_updated) VALUES (?, 0, NULL, ?)",
                (i, now)
            )
        conn.commit()
        conn.close()

    def clear_all_data(self):
        """Xóa toàn bộ dữ liệu báo cáo"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM parking_events")
        c.execute("DELETE FROM slot_status")
        c.execute("DELETE FROM license_plates")
        conn.commit()
        conn.close()


    def record_license_plate(self, plate_text, plate_image_bytes=None):
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO license_plates (plate_text, plate_image, timestamp) VALUES (?, ?, ?)",
            (plate_text, plate_image_bytes, now)
        )
        conn.commit()
        conn.close()

    def get_license_plates(self, limit=20):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM license_plates ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def _build_where_clause(self, start_dt=None, end_dt=None, start_time=None, end_time=None):
        where_clauses = []
        params = []

        if start_dt:
            where_clauses.append("timestamp >= ?")
            params.append(start_dt)
        if end_dt:
            where_clauses.append("timestamp <= ?")
            params.append(end_dt)

        if start_time:
            if len(start_time) == 5:
                start_time += ":00"
            where_clauses.append("strftime('%H:%M:%S', timestamp) >= ?")
            params.append(start_time)

        if end_time:
            if len(end_time) == 5:
                end_time += ":59"
            where_clauses.append("strftime('%H:%M:%S', timestamp) <= ?")
            params.append(end_time)

        where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        return where_str, params

    def get_filtered_events(self, start_dt=None, end_dt=None, start_time=None, end_time=None):
        conn = self._get_conn()
        c = conn.cursor()
        where_str, params = self._build_where_clause(start_dt, end_dt, start_time, end_time)
        query = f"SELECT * FROM parking_events{where_str} ORDER BY id ASC"
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_filtered_license_plates(self, start_dt=None, end_dt=None, start_time=None, end_time=None):
        conn = self._get_conn()
        c = conn.cursor()
        where_str, params = self._build_where_clause(start_dt, end_dt, start_time, end_time)
        query = f"SELECT * FROM license_plates{where_str} ORDER BY id ASC"
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_filtered_slot_summary(self, start_dt=None, end_dt=None, start_time=None, end_time=None):
        conn = self._get_conn()
        c = conn.cursor()
        where_str, params = self._build_where_clause(start_dt, end_dt, start_time, end_time)
        query = f"""
            SELECT slot_id, 
                   SUM(CASE WHEN event_type='IN' THEN 1 ELSE 0 END) as total_in,
                   SUM(CASE WHEN event_type='OUT' THEN 1 ELSE 0 END) as total_out
            FROM parking_events
            {where_str}
            GROUP BY slot_id
            ORDER BY slot_id
        """
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_filtered_stats(self, start_dt=None, end_dt=None, start_time=None, end_time=None):
        conn = self._get_conn()
        c = conn.cursor()
        where_str, params = self._build_where_clause(start_dt, end_dt, start_time, end_time)
        
        # Where clause with event_type condition
        if where_str:
            where_in = where_str + " AND event_type='IN'"
            where_out = where_str + " AND event_type='OUT'"
        else:
            where_in = " WHERE event_type='IN'"
            where_out = " WHERE event_type='OUT'"

        c.execute(f"SELECT COUNT(*) as cnt FROM parking_events{where_in}", params)
        total_in = c.fetchone()["cnt"]

        c.execute(f"SELECT COUNT(*) as cnt FROM parking_events{where_out}", params)
        total_out = c.fetchone()["cnt"]

        conn.close()
        return {
            "total_in": total_in,
            "total_out": total_out
        }

