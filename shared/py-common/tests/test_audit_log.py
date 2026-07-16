from __future__ import annotations

from sc_tpcrs_common.audit_log import GENESIS_HASH, build_audit_entry, verify_chain


def test_first_entry_chains_from_genesis():
    entry = build_audit_entry(
        prev_hash=GENESIS_HASH, actor="user:1", action="CREATE", resource="vendor:abc"
    )
    assert entry["prev_hash"] == GENESIS_HASH
    assert len(entry["hash"]) == 64


def test_verify_chain_accepts_valid_chain():
    entry1 = build_audit_entry(prev_hash=GENESIS_HASH, actor="user:1", action="CREATE", resource="vendor:abc")
    entry2 = build_audit_entry(prev_hash=entry1["hash"], actor="user:1", action="UPDATE", resource="vendor:abc")
    assert verify_chain([entry1, entry2]) is True


def test_verify_chain_detects_tampering():
    entry1 = build_audit_entry(prev_hash=GENESIS_HASH, actor="user:1", action="CREATE", resource="vendor:abc")
    entry2 = build_audit_entry(prev_hash=entry1["hash"], actor="user:1", action="UPDATE", resource="vendor:abc")
    tampered = dict(entry2)
    tampered["action"] = "DELETE"  # mutate without recomputing hash
    assert verify_chain([entry1, tampered]) is False


def test_verify_chain_detects_reordering():
    entry1 = build_audit_entry(prev_hash=GENESIS_HASH, actor="user:1", action="CREATE", resource="vendor:abc")
    entry2 = build_audit_entry(prev_hash=entry1["hash"], actor="user:1", action="UPDATE", resource="vendor:abc")
    assert verify_chain([entry2, entry1]) is False
