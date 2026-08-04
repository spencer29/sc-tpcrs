"""Neo4j dependency-graph writer + analytics (Module 3, pipeline stage iii).

sbom-service is the sole writer of the Vendor -> SoftwareComponent ->
Vulnerability graph whose constraints live in
infrastructure/neo4j/init-constraints.cypher. Ingestion MERGEs nodes/edges so
re-ingesting the same SBOM is idempotent.

Design stance (mirrors kafka_base.py): the graph is an *enhancement* over the
relational cross-reference, never the only path. If Neo4j is unreachable, the
writer logs and returns -- ingestion still succeeds and the relational data is
authoritative. Read paths degrade to an empty graph rather than erroring.

Analytics: Neo4j Community lacks the GDS plugin, so betweenness centrality /
PageRank / Louvain (the blueprint's GDS asks) are computed with networkx over
the fetched subgraph -- a documented, faithful equivalent. Target: centrality
under 3s on a 1,000-node graph, which networkx meets comfortably at this size.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import networkx as nx
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from ..config import settings

logger = logging.getLogger("sbom-service.graph")

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def _session():
    driver = _get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        await session.close()


async def health() -> bool:
    if not settings.neo4j_enabled:
        return False
    try:
        async with _session() as s:
            await s.run("RETURN 1")
        return True
    except (ServiceUnavailable, Neo4jError, OSError) as exc:
        logger.warning("Neo4j health check failed: %s", exc)
        return False


async def upsert_vendor_subgraph(
    *, vendor_id: str, vendor_name: str, tier: str | None, scanned: list
) -> bool:
    """MERGE the vendor and each component/vulnerability. `scanned` is a list of
    cve_scanner.ScannedComponent. Returns True on success, False if Neo4j is
    unavailable (ingestion continues regardless)."""
    if not settings.neo4j_enabled:
        return False

    payload = [
        {
            "purl": sc.component.purl,
            "name": sc.component.name,
            "version": sc.component.version,
            "ecosystem": sc.component.ecosystem,
            "vulns": [
                {
                    "cve_id": v.cve_id,
                    "severity": v.severity,
                    "cvss": v.cvss_score,
                    "kev": v.kev_flag,
                    "ssvc": v.ssvc_priority,
                }
                for v in sc.vulnerabilities
            ],
        }
        for sc in scanned
    ]

    cypher = """
    MERGE (v:Vendor {id: $vendor_id})
      SET v.name = $vendor_name, v.risk_tier = $tier
    WITH v
    UNWIND $components AS comp
      MERGE (c:SoftwareComponent {purl: comp.purl})
        SET c.name = comp.name, c.version = comp.version, c.ecosystem = comp.ecosystem
      MERGE (v)-[:PROVIDES]->(c)
      WITH c, comp
      UNWIND comp.vulns AS vuln
        MERGE (vu:Vulnerability {cve_id: vuln.cve_id})
          SET vu.severity = vuln.severity, vu.cvss = vuln.cvss,
              vu.kev = vuln.kev, vu.ssvc = vuln.ssvc
        MERGE (c)-[:AT_RISK]->(vu)
    """
    try:
        async with _session() as s:
            await s.run(
                cypher,
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                tier=tier,
                components=payload,
            )
        return True
    except (ServiceUnavailable, Neo4jError, OSError) as exc:
        logger.warning("Neo4j subgraph upsert failed (ingestion continues): %s", exc)
        return False


async def _fetch_graph_triples(vendor_id: str | None):
    """Return (vendor_rows, provides_rows, at_risk_rows). Empty lists if Neo4j down."""
    where = "WHERE v.id = $vendor_id" if vendor_id else ""
    cypher = f"""
    MATCH (v:Vendor)-[:PROVIDES]->(c:SoftwareComponent)
    {where}
    OPTIONAL MATCH (c)-[:AT_RISK]->(vu:Vulnerability)
    RETURN v.id AS vendor_id, v.name AS vendor_name, v.risk_tier AS tier,
           c.purl AS purl, c.name AS comp_name,
           vu.cve_id AS cve_id, vu.severity AS severity
    """
    try:
        async with _session() as s:
            result = await s.run(cypher, vendor_id=vendor_id)
            return [r.data() async for r in result]
    except (ServiceUnavailable, Neo4jError, OSError) as exc:
        logger.warning("Neo4j graph fetch failed; returning empty graph: %s", exc)
        return []


async def get_supply_chain_graph(vendor_id: str | None = None) -> dict:
    """Build a nodes+edges view for the frontend force-directed graph, annotated
    with betweenness centrality so critical-path vendors can be highlighted."""
    rows = await _fetch_graph_triples(vendor_id)

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    edge_seen: set[tuple[str, str, str]] = set()

    def add_edge(src: str, tgt: str, etype: str) -> None:
        key = (src, tgt, etype)
        if key not in edge_seen:
            edge_seen.add(key)
            edges.append({"source": src, "target": tgt, "type": etype})

    g = nx.Graph()

    for r in rows:
        vid = f"vendor:{r['vendor_id']}"
        cid = f"component:{r['purl']}"
        nodes.setdefault(
            vid, {"id": vid, "label": "Vendor", "name": r["vendor_name"] or r["vendor_id"], "tier": r.get("tier")}
        )
        nodes.setdefault(cid, {"id": cid, "label": "SoftwareComponent", "name": r["comp_name"] or r["purl"]})
        add_edge(vid, cid, "PROVIDES")
        g.add_edge(vid, cid)

        if r.get("cve_id"):
            nid = f"vuln:{r['cve_id']}"
            nodes.setdefault(
                nid, {"id": nid, "label": "Vulnerability", "name": r["cve_id"], "severity": r.get("severity")}
            )
            add_edge(cid, nid, "AT_RISK")

    # Betweenness centrality over the vendor/component graph (exclude vuln leaves
    # from the metric so it reflects supply-chain structure, not CVE fan-out).
    if g.number_of_nodes() > 2:
        try:
            centrality = nx.betweenness_centrality(g)
        except Exception:  # noqa: BLE001 - analytics must never break the view
            centrality = {}
        if centrality:
            threshold = sorted(centrality.values(), reverse=True)
            cutoff = threshold[min(2, len(threshold) - 1)]  # top ~3 as critical
            for node_id, score in centrality.items():
                if node_id in nodes:
                    nodes[node_id]["centrality"] = round(score, 4)
                    nodes[node_id]["critical_path"] = score >= cutoff and score > 0

    return {"nodes": list(nodes.values()), "edges": edges}


async def get_critical_path_vendors(limit: int = 10) -> list[dict]:
    """Betweenness + PageRank over the whole vendor/component graph -> the
    vendors whose compromise would cascade widest (blueprint's critical-path
    vendor identification)."""
    rows = await _fetch_graph_triples(None)
    g = nx.Graph()
    vendor_names: dict[str, str] = {}
    vendor_components: dict[str, set[str]] = {}

    for r in rows:
        vid = f"vendor:{r['vendor_id']}"
        cid = f"component:{r['purl']}"
        vendor_names[vid] = r["vendor_name"] or r["vendor_id"]
        vendor_components.setdefault(vid, set()).add(cid)
        g.add_edge(vid, cid)

    if g.number_of_nodes() == 0:
        return []

    try:
        betweenness = nx.betweenness_centrality(g)
        pagerank = nx.pagerank(g)
    except Exception:  # noqa: BLE001
        betweenness, pagerank = {}, {}

    out = []
    for vid, name in vendor_names.items():
        raw_id = vid.split(":", 1)[1]
        out.append(
            {
                "vendor_id": raw_id,
                "name": name,
                "betweenness": round(betweenness.get(vid, 0.0), 4),
                "pagerank": round(pagerank.get(vid, 0.0), 4),
                "dependent_component_count": len(vendor_components.get(vid, set())),
            }
        )
    out.sort(key=lambda v: (v["betweenness"], v["pagerank"]), reverse=True)
    return out[:limit]
