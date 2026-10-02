# ============================================================
# 告警接口: 告警列表 / 确认解决告警
# ============================================================

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db
from models import Alert
from schemas import AlertOut

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    status: str = Query("", description="triggered / resolved / 空=全部"),
    db: Session = Depends(get_db),
):
    """告警列表"""
    query = db.query(Alert).order_by(desc(Alert.id))
    if status:
        query = query.filter(Alert.status == status)
    return query.limit(100).all()


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """确认并解决告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert.status = "resolved"
    alert.resolved_at = datetime.now()
    db.commit()
    db.refresh(alert)
    return alert
