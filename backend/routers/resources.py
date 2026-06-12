from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text

from backend.dependencies import get_db, get_current_user, get_accessible_account_ids
from backend.models.user import User
from backend.models.resource import Resource
from backend.schemas.resource import ResourceResponse, ResourceSummary

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])


def _tag_filter_clause(tag_key: str, tag_value: str | None):
    """
    Build a SQLite JSON subquery that checks if a tag with the given key (and optionally value) exists.
    Uses json_each() to iterate the tags JSON array at the DB level — no Python in-memory scan.
    """
    if tag_value is not None:
        return text(
            "EXISTS ("
            "  SELECT 1 FROM json_each(resources.tags) AS je"
            "  WHERE json_extract(je.value, '$.Key') = :tag_key"
            "  AND json_extract(je.value, '$.Value') = :tag_value"
            ")"
        ).bindparams(tag_key=tag_key, tag_value=tag_value)
    else:
        return text(
            "EXISTS ("
            "  SELECT 1 FROM json_each(resources.tags) AS je"
            "  WHERE json_extract(je.value, '$.Key') = :tag_key"
            ")"
        ).bindparams(tag_key=tag_key)


@router.get("/", response_model=list[ResourceResponse])
def list_resources(
    account_id: int | None = Query(None),
    region: str | None = Query(None),
    resource_type: str | None = Query(None),
    tag_key: str | None = Query(None),
    tag_value: str | None = Query(None),
    idle_only: bool = Query(False),
    untagged_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible = get_accessible_account_ids(current_user, db)
    query = db.query(Resource)

    if accessible is not None:
        query = query.filter(Resource.account_id.in_(accessible))
    if account_id:
        query = query.filter(Resource.account_id == account_id)
    if region:
        query = query.filter(Resource.region == region)
    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)
    if idle_only:
        query = query.filter(Resource.is_idle == True)
    if untagged_only:
        query = query.filter(Resource.is_untagged == True)
    if tag_key:
        query = query.filter(_tag_filter_clause(tag_key, tag_value))

    return query.offset(skip).limit(limit).all()


@router.get("/summary", response_model=list[ResourceSummary])
def resource_summary(
    account_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible = get_accessible_account_ids(current_user, db)
    query = db.query(
        Resource.resource_type,
        func.count(Resource.id).label("count"),
        func.sum(case((Resource.is_idle == True, 1), else_=0)).label("idle_count"),
        func.sum(case((Resource.is_untagged == True, 1), else_=0)).label("untagged_count"),
    )

    if accessible is not None:
        query = query.filter(Resource.account_id.in_(accessible))
    if account_id:
        query = query.filter(Resource.account_id == account_id)

    rows = query.group_by(Resource.resource_type).all()
    return [
        ResourceSummary(
            resource_type=r[0],
            count=r[1],
            idle_count=int(r[2] or 0),
            untagged_count=int(r[3] or 0),
        )
        for r in rows
    ]


@router.get("/{resource_db_id}", response_model=ResourceResponse)
def get_resource(resource_db_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resource = db.query(Resource).filter(Resource.id == resource_db_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    accessible = get_accessible_account_ids(current_user, db)
    if accessible is not None and resource.account_id not in accessible:
        raise HTTPException(status_code=403, detail="No access")
    return resource
