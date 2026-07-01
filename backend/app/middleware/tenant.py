from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db, set_tenant


def get_tenant_db(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Session:
    """RLS uygulanmış DB session'ı döner. Route'lar bunu kullanmalı, get_db'yi doğrudan değil."""
    set_tenant(db, current_user["office_id"])
    return db
