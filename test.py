import sys
sys.path.append('.')
from TEST.database import SessionLocal
from TEST.models import Tracking

db = SessionLocal()

# Check count
print(f"Total: {db.query(Tracking).count()}")

# View all
for t in db.query(Tracking).all():
    print(f"{t.id}: {t.tracking_number} ({t.courier_code})")

# Get latest
latest = db.query(Tracking).order_by(Tracking.id.desc()).first()
print(f"Latest: {latest.tracking_number if latest else 'None'}")

db.close()