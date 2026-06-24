"""FastAPI web application for the AI Autonomous Systems platform.

Exposes the orchestrator capabilities as a REST API, enabling integration
with external tools, dashboards, and third-party services.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from src.orchestrator import Orchestrator, OrchestratorConfig

app = FastAPI(
    title="lippytm.ai – AI Autonomous Systems",
    description=(
        "Full-stack AI integration platform for all lippytm GitHub repositories. "
        "Provides autonomous content generation, advertising management, research, "
        "bot management, and Web3 integration."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(OrchestratorConfig())
    return _orchestrator


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------

class ContentRequest(BaseModel):
    repo_name: str
    content_type: str = "blog_post"
    topic: str = ""


class AdCampaignRequest(BaseModel):
    repo_name: str
    channel: str = "twitter"
    target_audience: str = "developers"
    budget_usd: float = 100.0


class BotMessageRequest(BaseModel):
    bot_id: str
    message: str


class DeFiAnalysisRequest(BaseModel):
    protocol: str
    tvl_usd: float
    apy: float
    risk_level: str = "medium"


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/", tags=["health"])
def root() -> dict:
    """Health check and platform info."""
    orch = get_orchestrator()
    status = orch.get_status()
    return {
        "platform": "lippytm.ai – AI Autonomous Systems",
        "status": "running",
        "total_repos": status.total_repos,
        "agents": status.agents_active,
        "docs": "/docs",
    }


@app.get("/status", tags=["health"])
def status() -> dict:
    """Detailed orchestrator status."""
    orch = get_orchestrator()
    s = orch.get_status()
    return {
        "running": s.running,
        "total_repos": s.total_repos,
        "agents_active": s.agents_active,
        "last_sync": s.last_sync,
        "last_health_check": s.last_health_check,
        "portfolio_health_score": s.portfolio_health_score,
        "generated_at": s.generated_at,
    }


# -- Repositories --

@app.get("/repos", tags=["repositories"])
def list_repos() -> dict:
    """List all lippytm repositories with metadata."""
    orch = get_orchestrator()
    repos = orch.sync_repositories()
    return {"total": len(repos), "repositories": repos}


@app.get("/repos/summary", tags=["repositories"])
def portfolio_summary() -> dict:
    """Return a high-level portfolio summary."""
    orch = get_orchestrator()
    return orch.get_portfolio_summary()


@app.get("/repos/integrations", tags=["repositories"])
def integration_opportunities() -> dict:
    """Identify integration opportunities across repositories."""
    orch = get_orchestrator()
    opps = orch.get_integration_opportunities()
    return {"total": len(opps), "opportunities": opps}


# -- Quality --

@app.get("/quality/health", tags=["quality"])
def health_check() -> dict:
    """Run a QA health check across all repositories."""
    orch = get_orchestrator()
    return orch.run_health_check()


# -- Content generation --

@app.post("/content/generate", tags=["content"])
def generate_content(req: ContentRequest) -> dict:
    """Generate AI content for a repository."""
    orch = get_orchestrator()
    return orch.generate_content(req.repo_name, req.content_type, req.topic)


@app.get("/content/digest", tags=["content"])
def portfolio_digest() -> dict:
    """Generate a weekly digest covering all repositories."""
    orch = get_orchestrator()
    return orch.generate_portfolio_digest()


# -- Advertising --

@app.post("/ads/campaign", tags=["advertising"])
def create_campaign(req: AdCampaignRequest) -> dict:
    """Create an AI-generated ad campaign."""
    orch = get_orchestrator()
    try:
        return orch.create_ad_campaign(req.repo_name, req.channel, req.target_audience, req.budget_usd)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/ads/report", tags=["advertising"])
def ad_report() -> dict:
    """Return the advertising portfolio performance report."""
    orch = get_orchestrator()
    return orch.get_ad_report()


# -- Research --

@app.get("/research/report", tags=["research"])
def research_report(focus: str = Query(default="", description="Optional focus area")) -> dict:
    """Run an AI research analysis on the portfolio."""
    orch = get_orchestrator()
    return orch.run_research(focus_area=focus or None)


@app.get("/research/trends", tags=["research"])
def technology_trends() -> dict:
    """Return a technology trend analysis."""
    orch = get_orchestrator()
    return orch.research_agent.generate_technology_trend_report()


# -- Bots --

@app.get("/bots/fleet", tags=["bots"])
def bot_fleet() -> dict:
    """Return status of all managed bots."""
    orch = get_orchestrator()
    return orch.get_bot_fleet_status()


@app.post("/bots/message", tags=["bots"])
def bot_message(req: BotMessageRequest) -> dict:
    """Send a message to a bot and receive an AI response."""
    orch = get_orchestrator()
    try:
        return orch.send_bot_message(req.bot_id, req.message)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# -- Web3 --

@app.get("/web3/networks", tags=["web3"])
def web3_networks() -> dict:
    """Return supported blockchain networks summary."""
    orch = get_orchestrator()
    return orch.get_web3_summary()


@app.post("/web3/defi/analyse", tags=["web3"])
def defi_analysis(req: DeFiAnalysisRequest) -> dict:
    """Run AI-powered DeFi analysis."""
    orch = get_orchestrator()
    return orch.analyse_defi(req.protocol, req.tvl_usd, req.apy, req.risk_level)
