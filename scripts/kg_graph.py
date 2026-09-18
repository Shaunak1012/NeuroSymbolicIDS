"""
kg_graph.py — the adaptive Knowledge Graph class, importable.

Moved here VERBATIM from kg.py on 2026-09-16 (audit F-22). kg.py is a script with
top-level execution, so it cannot be imported, and latency.py used to lift this
class out of kg.py's source with exec(compile(ast...)) to be sure it timed exactly
the code kg.py runs. Both now import it from here, which gives the same guarantee
without exec. The move was checked by comparing the class's AST before and after.
"""
import numpy as np
import networkx as nx

import behavior


class KnowledgeGraph:
    """Adaptive memory: typed nodes, decaying weighted edges, growth tracking."""

    def __init__(self, k, behaviours, decay_tau):
        self.G = nx.DiGraph()
        self.k = k
        self.behaviours = behaviours
        self.tau = decay_tau
        self.decay_factor = float(np.exp(-1.0 / decay_tau))
        self.history = {c: [] for c in range(k)}      # per-window activity counts
        for c in range(k):
            self.G.add_node(f"Cluster:{c}", kind="Cluster", cid=c, activity=0.0)
        for b in behaviours:
            self.G.add_node(f"Behaviour:{b}", kind="Behaviour",
                            binary=(behavior.BEHAVIOUR_KIND[b] == "binary"))

    # -- edge helpers ---------------------------------------------------------
    def _reinforce(self, u, v, rel, amount):
        if amount <= 0:
            return
        if self.G.has_edge(u, v):
            self.G[u][v]["weight"] += amount
        else:
            self.G.add_edge(u, v, weight=amount, rel=rel)

    def decay(self):
        """Exponential decay of every edge. This is the 'adaptive' mechanism:
        associations not reinforced recently fade out of memory."""
        for _, _, d in self.G.edges(data=True):
            d["weight"] *= self.decay_factor
        for _, d in self.G.nodes(data=True):
            if d["kind"] == "Cluster":
                d["activity"] *= self.decay_factor

    # -- observation ----------------------------------------------------------
    def observe(self, labels, beh, classes=None, record_history=True):
        """Ingest a batch of flows: reinforce exhibits/associated_with edges."""
        for c in np.unique(labels):
            m = labels == c
            n = int(m.sum())
            cn = f"Cluster:{c}"
            self.G.nodes[cn]["activity"] += n
            # exhibits: mean behaviour strength in this batch of the cluster
            means = beh[m].mean(0)
            for bi, bname in enumerate(self.behaviours):
                self._reinforce(cn, f"Behaviour:{bname}", "exhibits",
                                float(means[bi]) * n)
            # associated_with: only when labels are known (i.e. training memory)
            if classes is not None:
                vals, cnts = np.unique(classes[m], return_counts=True)
                for v, ct in zip(vals, cnts):
                    an = f"AttackType:{v}"
                    if an not in self.G:
                        self.G.add_node(an, kind="AttackType", name=str(v))
                    self._reinforce(cn, an, "associated_with", float(ct))
        if record_history:
            counts = np.bincount(labels, minlength=self.k)
            for c in range(self.k):
                self.history[c].append(int(counts[c]))

    # -- emerging patterns ----------------------------------------------------
    def burstiness(self):
        """Peak-window share / uniform share, per cluster. 1.0 = flat in time.

        This is the ONLY emerging-pattern criterion that survived measurement.
        Computed from cluster ids + arrival order alone -- no labels.
        """
        out = np.zeros(self.k)
        for c, h in self.history.items():
            h = np.asarray(h, dtype=float)
            if h.sum() <= 0:
                continue
            out[c] = (h / h.sum()).max() * len(h)
        return out

    def emerging(self, threshold):
        return set(np.flatnonzero(self.burstiness() >= threshold).tolist())

    # -- explanation ----------------------------------------------------------
    def top_edges(self, cid, rel, n=3):
        cn = f"Cluster:{cid}"
        es = [(v, d["weight"]) for _, v, d in self.G.out_edges(cn, data=True)
              if d["rel"] == rel]
        tot = sum(w for _, w in es) or 1.0
        return sorted(((v.split(":", 1)[1], w / tot) for v, w in es),
                      key=lambda t: -t[1])[:n]

    def explain(self, cid, burst, is_emerging):
        """A human-readable reasoning path — the KG's actual deliverable."""
        beh = self.top_edges(cid, "exhibits")
        atk = self.top_edges(cid, "associated_with")
        known = ", ".join(f"{a} {p:.0%}" for a, p in atk) if atk else "no known attack"
        bstr = ", ".join(f"{b} {p:.0%}" for b, p in beh) if beh else "none"
        verdict = ("EMERGING — activity concentrated in time"
                   if is_emerging else "stable — activity spread across the capture")
        return {
            "cluster": cid, "burstiness": round(float(burst), 2),
            "emerging": bool(is_emerging),
            "dominant_behaviours": beh, "known_associations": atk,
            "path": (f"Cluster:{cid} -[exhibits]-> [{bstr}] | "
                     f"-[associated_with]-> [{known}] | {verdict} "
                     f"(burstiness {burst:.1f}x uniform)"),
        }
