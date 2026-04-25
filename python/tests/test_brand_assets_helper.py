from unittest.mock import MagicMock, patch
from content_engine.utils import brand_assets


def _mock_db_with_rows(rows):
    m = MagicMock()
    chain = m.table.return_value.select.return_value.eq.return_value.eq.return_value \
             .order.return_value.limit.return_value.execute.return_value
    chain.data = rows
    return m


def test_get_brand_palette_returns_hex_list():
    rows = [{"id":"a","kind":"palette","label":"core","storage_path":"p","mime_type":"image/png",
             "palette_hex":["#111111","#222222"],"metadata":{}}]
    with patch.object(brand_assets, "get_db", return_value=_mock_db_with_rows(rows)):
        assert brand_assets.get_brand_palette("brand-x") == ["#111111","#222222"]


def test_get_brand_palette_empty_when_no_asset():
    with patch.object(brand_assets, "get_db", return_value=_mock_db_with_rows([])):
        assert brand_assets.get_brand_palette("brand-x") == []
