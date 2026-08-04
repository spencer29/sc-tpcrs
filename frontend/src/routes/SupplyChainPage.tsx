import { Loader2, Network, Search, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { getCriticalPathVendors, getCveImpact, getSupplyChainGraph, ingestSbom } from "../api/sbom";
import { listVendors } from "../api/vendors";
import { RoleGate } from "../auth/RoleGate";
import type { CriticalPathVendor, GraphNode, SbomComponent, SupplyChainGraph } from "../types/sbom";
import type { Vendor } from "../types/vendor";

// A left-pad@1.0.0 CycloneDX SBOM. This exact component/version is the
// "planted" finding (see shared adapters/planted.py) that reliably resolves to
// the CRITICAL, KEV-listed CVE-2024-99999 -- Demo Scenario 1.
const SAMPLE_SBOM = JSON.stringify(
  {
    bomFormat: "CycloneDX",
    specVersion: "1.6",
    metadata: { component: { name: "demo-payment-app", type: "application" } },
    components: [
      { type: "library", name: "left-pad", version: "1.0.0", purl: "pkg:npm/left-pad@1.0.0" },
      { type: "library", name: "express", version: "4.18.2", purl: "pkg:npm/express@4.18.2" },
      { type: "library", name: "lodash", version: "4.17.21", purl: "pkg:npm/lodash@4.17.21" },
    ],
  },
  null,
  2,
);

const NODE_COLORS: Record<string, string> = {
  Vendor: "hsl(217 91% 60%)",
  SoftwareComponent: "hsl(174 62% 47%)",
  Vulnerability: "hsl(0 84% 60%)",
};

interface Positioned extends GraphNode {
  x: number;
  y: number;
}

/** Tiny dependency-free force-directed layout. Deterministic seed positions +
 * fixed iteration count keep it cheap and stable across renders. */
function layout(graph: SupplyChainGraph, width: number, height: number): Positioned[] {
  const n = graph.nodes.length;
  if (n === 0) return [];
  const nodes: Positioned[] = graph.nodes.map((node, i) => {
    const angle = (i / n) * Math.PI * 2;
    return { ...node, x: width / 2 + Math.cos(angle) * 160, y: height / 2 + Math.sin(angle) * 160 };
  });
  const index = new Map(nodes.map((nd, i) => [nd.id, i]));
  const edges = graph.edges
    .map((e) => [index.get(e.source), index.get(e.target)] as [number | undefined, number | undefined])
    .filter(([a, b]) => a !== undefined && b !== undefined) as [number, number][];

  const ITER = 220;
  const k = Math.sqrt((width * height) / Math.max(1, n)); // ideal edge length
  for (let it = 0; it < ITER; it++) {
    const disp = nodes.map(() => ({ dx: 0, dy: 0 }));
    // repulsion (all pairs)
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let dx = nodes[i].x - nodes[j].x;
        let dy = nodes[i].y - nodes[j].y;
        let dist = Math.hypot(dx, dy) || 0.01;
        const force = (k * k) / dist;
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        disp[i].dx += dx;
        disp[i].dy += dy;
        disp[j].dx -= dx;
        disp[j].dy -= dy;
      }
    }
    // attraction (edges)
    for (const [a, b] of edges) {
      let dx = nodes[a].x - nodes[b].x;
      let dy = nodes[a].y - nodes[b].y;
      const dist = Math.hypot(dx, dy) || 0.01;
      const force = (dist * dist) / k;
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      disp[a].dx -= dx;
      disp[a].dy -= dy;
      disp[b].dx += dx;
      disp[b].dy += dy;
    }
    const temp = 10 * (1 - it / ITER);
    for (let i = 0; i < n; i++) {
      const d = Math.hypot(disp[i].dx, disp[i].dy) || 0.01;
      nodes[i].x += (disp[i].dx / d) * Math.min(d, temp);
      nodes[i].y += (disp[i].dy / d) * Math.min(d, temp);
      nodes[i].x = Math.max(24, Math.min(width - 24, nodes[i].x));
      nodes[i].y = Math.max(24, Math.min(height - 24, nodes[i].y));
    }
  }
  return nodes;
}

export function SupplyChainPage() {
  const [graph, setGraph] = useState<SupplyChainGraph>({ nodes: [], edges: [] });
  const [critical, setCritical] = useState<CriticalPathVendor[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ingest panel
  const [selectedVendor, setSelectedVendor] = useState("");
  const [sbomText, setSbomText] = useState(SAMPLE_SBOM);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);

  // CVE impact search (Demo Scenario 1)
  const [cveQuery, setCveQuery] = useState("CVE-2024-99999");
  const [impact, setImpact] = useState<SbomComponent[] | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);

  const width = 720;
  const height = 440;
  const positioned = useMemo(() => layout(graph, width, height), [graph]);
  const nodeById = useMemo(() => new Map(positioned.map((p) => [p.id, p])), [positioned]);

  const reloadRef = useRef(0);
  async function reload() {
    setLoading(true);
    try {
      const [g, c] = await Promise.all([getSupplyChainGraph(), getCriticalPathVendors(8)]);
      setGraph(g);
      setCritical(c);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load supply-chain graph");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    listVendors({ size: 100 })
      .then((r) => {
        setVendors(r.items);
        if (r.items.length) setSelectedVendor(r.items[0].id);
      })
      .catch(() => undefined);
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadRef.current]);

  async function handleIngest() {
    if (!selectedVendor) return;
    setIngesting(true);
    setIngestMsg(null);
    try {
      const resp = await ingestSbom(selectedVendor, sbomText, "Uploaded via Supply Chain console");
      setIngestMsg(
        `Ingested ${resp.document.component_count} components in ${resp.processing_ms.toFixed(0)}ms — ` +
          `${resp.critical_vulnerabilities.length} critical/KEV finding(s).`,
      );
      await reload();
    } catch (err) {
      setIngestMsg(err instanceof ApiError ? `Error: ${err.message}` : "Ingestion failed");
    } finally {
      setIngesting(false);
    }
  }

  async function handleCveSearch() {
    if (!cveQuery.trim()) return;
    setImpactLoading(true);
    try {
      setImpact(await getCveImpact(cveQuery.trim()));
    } catch (err) {
      setImpact([]);
      setError(err instanceof ApiError ? err.message : "CVE lookup failed");
    } finally {
      setImpactLoading(false);
    }
  }

  const edgeLine = (source: string, target: string, i: number) => {
    const a = nodeById.get(source);
    const b = nodeById.get(target);
    if (!a || !b) return null;
    return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="hsl(var(--border))" strokeWidth={1} />;
  };

  const nodeRadius = (node: Positioned) =>
    node.label === "Vendor" ? (node.critical_path ? 13 : 10) : node.label === "SoftwareComponent" ? 7 : 5;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Supply Chain</h1>
        <p className="page-subtitle">
          SBOM dependency graph, CVE cross-referencing, and critical-path vendor analysis
        </p>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16, alignItems: "start" }}>
        {/* graph */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <Network size={16} />
            <strong>Dependency Graph</strong>
            <span style={{ marginLeft: "auto", fontSize: "0.8rem", color: "hsl(var(--muted-foreground))" }}>
              {graph.nodes.length} nodes · {graph.edges.length} edges
            </span>
          </div>
          {loading ? (
            <p>Loading graph...</p>
          ) : graph.nodes.length === 0 ? (
            <p style={{ color: "hsl(var(--muted-foreground))" }}>
              No SBOMs ingested yet. Use the panel on the right to ingest one and populate the graph.
            </p>
          ) : (
            <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ background: "hsl(var(--muted))", borderRadius: 8 }}>
              {graph.edges.map((e, i) => edgeLine(e.source, e.target, i))}
              {positioned.map((node) => (
                <g key={node.id}>
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={nodeRadius(node)}
                    fill={NODE_COLORS[node.label] ?? "hsl(var(--primary))"}
                    stroke={node.critical_path ? "hsl(38 92% 50%)" : "white"}
                    strokeWidth={node.critical_path ? 3 : 1}
                  />
                  {node.label !== "Vulnerability" && (
                    <text x={node.x + nodeRadius(node) + 3} y={node.y + 3} fontSize={10} fill="hsl(var(--foreground))">
                      {node.name.length > 22 ? `${node.name.slice(0, 22)}…` : node.name}
                    </text>
                  )}
                </g>
              ))}
            </svg>
          )}
          <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: "0.8rem", flexWrap: "wrap" }}>
            <Legend color={NODE_COLORS.Vendor} label="Vendor" />
            <Legend color={NODE_COLORS.SoftwareComponent} label="Component" />
            <Legend color={NODE_COLORS.Vulnerability} label="Vulnerability" />
            <Legend color="hsl(38 92% 50%)" label="Critical path (ring)" />
          </div>
        </div>

        {/* side panels */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <RoleGate allow={["risk_officer", "ciso", "admin"]}>
            <div className="card">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <Upload size={15} />
                <strong>Ingest SBOM</strong>
              </div>
              <select value={selectedVendor} onChange={(e) => setSelectedVendor(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
              <textarea
                value={sbomText}
                onChange={(e) => setSbomText(e.target.value)}
                rows={6}
                spellCheck={false}
                style={{ width: "100%", fontFamily: "monospace", fontSize: "0.72rem", resize: "vertical" }}
              />
              <button className="btn" onClick={handleIngest} disabled={ingesting || !selectedVendor} style={{ width: "100%", marginTop: 8, display: "inline-flex", justifyContent: "center", gap: 6 }}>
                {ingesting ? <Loader2 size={15} className="spin" /> : <Upload size={15} />} Ingest
              </button>
              {ingestMsg && (
                <p style={{ fontSize: "0.8rem", marginTop: 8, color: ingestMsg.startsWith("Error") ? "hsl(0 84% 60%)" : "hsl(142 71% 45%)" }}>
                  {ingestMsg}
                </p>
              )}
            </div>
          </RoleGate>

          <div className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <Search size={15} />
              <strong>CVE Impact</strong>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <input value={cveQuery} onChange={(e) => setCveQuery(e.target.value)} placeholder="CVE-2024-99999" style={{ flex: 1 }} />
              <button className="btn" onClick={handleCveSearch} disabled={impactLoading}>
                {impactLoading ? <Loader2 size={14} className="spin" /> : "Find"}
              </button>
            </div>
            {impact !== null && (
              <div style={{ marginTop: 8, fontSize: "0.82rem" }}>
                {impact.length === 0 ? (
                  <span style={{ color: "hsl(var(--muted-foreground))" }}>No affected components.</span>
                ) : (
                  <>
                    <div style={{ marginBottom: 4 }}>
                      <strong>{impact.length}</strong> affected component(s):
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 16 }}>
                      {impact.map((c) => (
                        <li key={c.id}>
                          <Link to={`/vendors/${c.vendor_id ?? ""}`}>{c.component_name}</Link> @ {c.version}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* critical-path vendors */}
      <div className="card" style={{ marginTop: 16 }}>
        <strong>Critical-Path Vendors</strong>
        <p className="page-subtitle" style={{ marginTop: 2 }}>
          Ranked by betweenness centrality &amp; PageRank — widest cascade on compromise
        </p>
        {critical.length === 0 ? (
          <p style={{ color: "hsl(var(--muted-foreground))" }}>No graph data yet.</p>
        ) : (
          <table style={{ marginTop: 8 }}>
            <thead>
              <tr>
                <th>Vendor</th>
                <th style={{ textAlign: "right" }}>Betweenness</th>
                <th style={{ textAlign: "right" }}>PageRank</th>
                <th style={{ textAlign: "right" }}>Components</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {critical.map((v) => (
                <tr key={v.vendor_id}>
                  <td>{v.name}</td>
                  <td className="mono" style={{ textAlign: "right" }}>{v.betweenness.toFixed(3)}</td>
                  <td className="mono" style={{ textAlign: "right" }}>{v.pagerank.toFixed(3)}</td>
                  <td className="mono" style={{ textAlign: "right" }}>{v.dependent_component_count}</td>
                  <td>
                    <Link to={`/vendors/${v.vendor_id}`}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, display: "inline-block" }} />
      {label}
    </span>
  );
}
