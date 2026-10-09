"""Helper de paginación común (R-04 / HU-11)."""

from sqlalchemy import select

from app.core.pagination import PageParams, paginate
from app.models.model_category import Category
from app.schemas.schema_category import CategoryOut


def _create_categories(db, n: int) -> None:
    db.add_all(Category(name=f"Cat {i}", sort_order=i)
               for i in range(1, n + 1))
    db.commit()


def test_offset_is_calculated_from_page_and_size():
    assert PageParams(page=1, size=20).offset == 0
    assert PageParams(page=3, size=20).offset == 40


def test_paginate_returns_items_and_total(db):
    _create_categories(db, 5)
    stmt = select(Category).order_by(Category.id)

    page = paginate(db, stmt, PageParams(page=2, size=2), CategoryOut)

    assert page.total == 5
    assert page.page == 2
    assert page.size == 2
    assert [c.name for c in page.items] == ["Cat 3", "Cat 4"]


def test_last_page_can_be_shorter(db):
    _create_categories(db, 5)
    stmt = select(Category).order_by(Category.id)

    page = paginate(db, stmt, PageParams(page=3, size=2), CategoryOut)

    assert [c.name for c in page.items] == ["Cat 5"]


def test_page_after_the_last_returns_empty_items(db):
    _create_categories(db, 2)
    stmt = select(Category).order_by(Category.id)

    page = paginate(db, stmt, PageParams(page=5, size=10), CategoryOut)

    assert page.items == []
    assert page.total == 2


def test_total_respects_filters(db):
    _create_categories(db, 5)
    stmt = select(Category).where(
        Category.sort_order > 3).order_by(Category.id)

    page = paginate(db, stmt, PageParams(page=1, size=20), CategoryOut)

    assert page.total == 2


def test_page_params_validation_in_real_endpoint(client, admin_headers):
    for params in ({"page": 0}, {"size": 0}, {"size": 101}):
        r = client.get("/dishes/", params=params, headers=admin_headers)
        assert r.status_code == 422
        assert r.json()["code"] == "validation_error"
