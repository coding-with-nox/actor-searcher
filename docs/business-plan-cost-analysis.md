# Actor-Searcher — Cost Analysis & Sustainability Plan

**Date:** 2026-05-23  
**Status:** Operational cost analysis for personal use → scaling options

---

## 1. Current Cost Problem

Today all API costs are borne by the actor/developer. The system has no cost recovery mechanism. This document:

1. Quantifies real monthly spend at different usage intensities
2. Identifies cost reduction levers
3. Proposes paths to sustainability (cost-neutral or profitable)

---

## 2. Monthly Cost Estimate

### Assumptions

| Parameter | Conservative | Moderate | Intensive |
|---|---|---|---|
| Runs per day | 2 (every 12h) | 4 (every 6h) | 24 (hourly) |
| Listings per run | 30 | 50 | 80 |
| LLM model | gpt-4.1-mini | gpt-4.1-mini | gpt-4.1-mini |
| Backstage enabled | No | Yes | Yes |
| Gmail enabled | No | Yes | Yes |

### OpenAI API Costs (gpt-4.1-mini)

Pricing reference: ~$0.15/1M input tokens, ~$0.60/1M output tokens

| Operation | Tokens per call | Calls/day (moderate) | Tokens/month |
|---|---|---|---|
| `generate_queries` | ~1,200 (in+out) | 4 | ~144,000 |
| `batch_match_profile` | ~5,000/batch, 3 batches | 4 | ~1,800,000 |
| `extract_deadline` | ~600 | ~30 | ~540,000 |
| **Total** | | | **~2,484,000** |

**Monthly OpenAI cost (moderate usage):** ~$0.50–$0.80

**Monthly OpenAI cost (intensive, hourly):** ~$6–$10

### Search API Costs

**Tavily:**

| Tier | Price | Credits/month | Sufficient for |
|---|---|---|---|
| Researcher (Free) | $0 | 1,000 | ~2 runs/day × 10 queries |
| Starter | $9/month | 10,000 | ~8 runs/day × 10 queries |
| Advanced | $29/month | 100,000 | Unlimited practical use |

With **moderate usage** (4 runs/day × 10 queries = 1,200/month): **$9/month (Starter)**  
With **conservative** (2 runs/day = 600/month): **Free tier** ✅

**Brave Search API:**
- Free tier: 2,000 queries/month (sufficient for conservative/moderate)
- $3 per 1,000 queries beyond free tier
- Can replace Tavily partially to reduce costs

### Infrastructure

| Option | Monthly Cost | Notes |
|---|---|---|
| **Local machine (always-on PC/Mac)** | ~€2–5 electricity | Best for personal use |
| **Raspberry Pi 4 (4GB)** | ~€1–2 electricity | Quiet, low power |
| **Hetzner CX22 VPS** | €4.85 | 2 vCPU, 4GB RAM, Germany |
| **DigitalOcean Droplet (Basic)** | $6 | 1 vCPU, 1GB RAM |
| **DigitalOcean Droplet (Standard)** | $12 | 1 vCPU, 2GB RAM (recommended) |

**Recommendation:** Run locally on an always-on machine (€2–5/month electricity) or Hetzner for €4.85/month.

### Total Monthly Cost Summary

| Scenario | OpenAI | Tavily | Infra | **Total** |
|---|---|---|---|---|
| Conservative (2×/day, local) | ~€0.40 | Free | ~€2 electricity | **~€2.50/month** |
| Moderate (4×/day, VPS) | ~€0.75 | €9 | ~€5 | **~€15/month** |
| Intensive (hourly, VPS) | ~€9 | €29 | ~€12 | **~€50/month** |

**Current realistic cost: €15–20/month** for moderate usage on a small VPS.

---

## 3. Cost Reduction Strategies

### Quick wins (implement immediately)

**A. Cache query generation**  
The actor's profile rarely changes. Cache generated queries for 24h. One LLM call per day instead of one per run.  
→ Saves ~80% of `generate_queries` cost.

```python
# In QueryGeneratorAgent: add TTL cache keyed on profile hash
import hashlib, time
_cache: dict[str, tuple[list[str], float]] = {}

async def execute(self, profile: ActorProfile) -> list[str]:
    key = hashlib.md5(profile.to_summary().encode()).hexdigest()
    if key in _cache and time.monotonic() - _cache[key][1] < 86400:
        return _cache[key][0]
    queries = await self.llm.generate_queries(profile.to_summary())
    _cache[key] = (queries, time.monotonic())
    return queries
```

**B. Persistent dedup across runs**  
Currently dedup is per-run. A cross-run dedup table (`seen_urls`) prevents re-evaluating listings already scored.  
→ In steady state (mostly repeat listings), saves 70–90% of LLM scoring cost.

**C. Brave Search as primary (free tier)**  
Use Brave Search API (2,000 free/month) as primary provider. Add Tavily only as fallback for specialized casting queries.  
→ Saves $9/month Tavily cost.

**D. Reduce run frequency in off-hours**  
Run every 2h 08:00–20:00, every 12h 20:00–08:00.  
→ Cuts runs from 24/day to ~10/day without missing deadlines.

### Medium-term (Phase 2–3)

**E. Self-host embedding model for dedup**  
Replace LLM-based semantic dedup with local embedding model (e.g. `nomic-embed-text` via Ollama).  
Cost: €0, requires 4GB+ RAM.

**F. Use Qdrant + local embeddings for ranking**  
Replace `batch_match_profile` LLM calls with vector similarity search.  
- Embed actor profile once per week: negligible cost
- Embed each listing locally: €0 with Ollama
- LLM only for rationale on top-10 results

**G. Tiered model strategy**  
| Task | Current Model | Optimized Model |
|---|---|---|
| Query generation | gpt-4.1-mini | gpt-4.1-nano or local |
| Profile matching (batch) | gpt-4.1-mini | Keep (quality-critical) |
| Deadline extraction | gpt-4.1-mini | gpt-4.1-nano |
| Rationale generation | gpt-4.1-mini | Keep (user-visible) |

Potential saving: 30–40% on OpenAI costs.

---

## 4. Break-Even & Revenue Scenarios

### Scenario A: Personal use (current)
**Target:** Cover costs yourself.  
**Cost:** €2.50–15/month depending on usage.  
**Action:** Implement cache + Brave free tier → cost drops to ~€5/month.

### Scenario B: Cost-sharing with the actor
The actor benefits directly. Split costs 50/50 or have actor pay subscription.  
**Pricing:** €10–25/month subscription from actor.  
**Margin at 1 actor:** Break-even to small surplus.

### Scenario C: Micro-SaaS for actors (1–10 clients)
Offer the service to other actors managed by the same agency, or as a personal product.

**Pricing model:**

| Tier | Price | What's included |
|---|---|---|
| Solo | €29/month | 1 actor, all sources, daily digest |
| Pro | €49/month | 1 actor, hourly, Telegram HITL, profile learning |

**Cost per actor (at scale, amortized infra):**
- OpenAI: ~€0.75/actor/month
- Tavily: ~€1/actor/month (shared searches)
- Infra: ~€1/actor/month

**Gross margin per actor:** ~€46/month (Pro tier) → ~94% margin.

**Break-even:** 1 paying actor covers all infrastructure costs.

**Legal note:** Reselling Backstage scraping as a service likely violates their ToS. In a commercial scenario, replace Backstage scraping with official casting API partnerships (Casting Networks has a partner API) or rely only on public/Tavily sources.

### Scenario D: Agency white-label (10+ actors)
Sell the system to a talent agency to use for their full roster.

**Pricing:** €200–500/month flat for up to 20 actors.  
**Implementation:** Multi-actor support (Phase 4 feature, ~3 weeks dev).  
**Market:** Boutique talent agencies in Italy managing 5–30 actors.

---

## 5. Recommended Short-Term Actions

1. **Implement query caching** (2h dev) → cuts OpenAI cost by 80%
2. **Add cross-run dedup** (1 day dev) → cuts scoring cost by 70% in steady state
3. **Switch Tavily → Brave for primary** (2h dev) → saves €9/month
4. **Set run frequency to 4×/day** (config change) → halves remaining costs
5. **Target cost: €3–5/month** for effective daily monitoring

---

## 6. Cost Dashboard (future)

Add a `/admin/costs` page that shows:
- LLM tokens used per day/month (track from run metadata)
- Estimated spend to date (tokens × current pricing)
- Projection to end of month
- Alerts if monthly spend exceeds configurable threshold

This makes costs visible and controllable rather than a black box.

---

## Summary

| Today | After optimizations |
|---|---|
| €15–20/month | €3–5/month |
| No visibility | Cost dashboard |
| All cost on developer | Shareable with actor |
| No revenue path | Clear micro-SaaS path if desired |

The system is already economically viable as a personal tool. The main lever is **cross-run dedup + query caching**, which reduces LLM calls from O(runs × listings) to O(new listings only).
