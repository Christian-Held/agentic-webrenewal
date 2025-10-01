import json

from webrenewal.postedit.models import ChangeOperation, ChangeSet, SiteState
from webrenewal.state import StateStore


def test_record_edit_serialises_complex_payload(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    change_set = ChangeSet(targets=["head"], operations=[ChangeOperation(type="head.patch", payload={})])
    state = SiteState()

    store.record_edit(
        scope="head",
        prompt="update head",
        change_set=change_set,
        diff_stats={"results": {"head": state}},
        llm_meta={"latency_ms": 120, "path": tmp_path / "file.txt"},
    )

    edits = store.list_edits()
    assert edits[0].change_set_hash == change_set.hash()

    with store._connect() as conn:  # Access private helper for verification in tests.
        row = conn.execute("SELECT diff_stats_json, llm_meta_json FROM edits LIMIT 1").fetchone()

    diff_payload = json.loads(row["diff_stats_json"])
    llm_payload = json.loads(row["llm_meta_json"])

    assert diff_payload["results"]["head"]["nav"] == {"items": [], "layout": {}, "html": ""}
    assert llm_payload["path"].endswith("file.txt")
