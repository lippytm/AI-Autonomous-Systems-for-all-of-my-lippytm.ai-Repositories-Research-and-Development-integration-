"""Web3 / Blockchain AI Agent.

Provides AI-powered Web3 integration for lippytm repositories including
wallet analysis, DeFi monitoring, NFT management, and smart contract
interaction for Web3AI, Factory.ai, and related projects.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Web3Network:
    """Configuration for a supported blockchain network."""

    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    native_token: str


@dataclass
class ContractInfo:
    """Basic information about a smart contract."""

    address: str
    network: str
    name: str
    abi_summary: list[str] = field(default_factory=list)
    deployed_at: str = ""
    verified: bool = False


@dataclass
class Web3Report:
    """Report from the Web3 agent."""

    network: str
    analysis_type: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")


# Supported networks
SUPPORTED_NETWORKS: dict[str, Web3Network] = {
    "ethereum": Web3Network(
        name="Ethereum Mainnet",
        chain_id=1,
        rpc_url=os.getenv("ETH_RPC_URL", "https://cloudflare-eth.com"),
        explorer_url="https://etherscan.io",
        native_token="ETH",
    ),
    "polygon": Web3Network(
        name="Polygon",
        chain_id=137,
        rpc_url=os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
        explorer_url="https://polygonscan.com",
        native_token="MATIC",
    ),
    "bsc": Web3Network(
        name="BNB Smart Chain",
        chain_id=56,
        rpc_url=os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org"),
        explorer_url="https://bscscan.com",
        native_token="BNB",
    ),
    "base": Web3Network(
        name="Base",
        chain_id=8453,
        rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        explorer_url="https://basescan.org",
        native_token="ETH",
    ),
}


class Web3Agent:
    """Autonomous Web3 and blockchain AI agent for lippytm repositories.

    Supports:
    - Wallet balance and transaction monitoring
    - Smart contract interaction via ABI
    - DeFi protocol monitoring (TVL, APY)
    - NFT portfolio tracking
    - AI-powered blockchain analysis and recommendations
    - Web3AI, Factory.ai, and AI-Time-Machines repo integration
    """

    def __init__(
        self,
        api_key: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        web3_rpc_url: str | None = None,
    ) -> None:
        self._provider = (provider or os.getenv("AI_PROVIDER", "openai")).lower()
        self._model = model or os.getenv("AI_MODEL", "gpt-4o")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
        self._rpc_url = web3_rpc_url or os.getenv("WEB3_RPC_URL", "")
        self._web3: Any = None
        self._contracts: dict[str, ContractInfo] = {}

    # ------------------------------------------------------------------
    # Web3 connectivity
    # ------------------------------------------------------------------

    def connect(self, network: str = "ethereum") -> bool:
        """Connect to a blockchain network."""
        net = SUPPORTED_NETWORKS.get(network)
        rpc = self._rpc_url or (net.rpc_url if net else "")
        if not rpc:
            return False
        try:
            from web3 import Web3  # type: ignore[import]
            self._web3 = Web3(Web3.HTTPProvider(rpc))
            return self._web3.is_connected()
        except ImportError:
            return False

    def is_connected(self) -> bool:
        return self._web3 is not None and self._web3.is_connected()

    # ------------------------------------------------------------------
    # Wallet operations
    # ------------------------------------------------------------------

    def get_wallet_balance(self, address: str, network: str = "ethereum") -> dict[str, Any]:
        """Get the native token balance for a wallet address."""
        if not self.is_connected():
            return self._mock_wallet_balance(address, network)
        try:
            balance_wei = self._web3.eth.get_balance(address)
            from web3 import Web3  # type: ignore[import]
            balance_eth = Web3.from_wei(balance_wei, "ether")
            net = SUPPORTED_NETWORKS.get(network)
            return {
                "address": address,
                "network": network,
                "balance": float(balance_eth),
                "token": net.native_token if net else "ETH",
                "checked_at": datetime.now(timezone.utc).isoformat() + "Z",
            }
        except Exception as exc:
            return {"error": str(exc), "address": address}

    def _mock_wallet_balance(self, address: str, network: str) -> dict[str, Any]:
        net = SUPPORTED_NETWORKS.get(network)
        return {
            "address": address,
            "network": network,
            "balance": 0.0,
            "token": net.native_token if net else "ETH",
            "note": "Not connected to Web3 node – install web3 and configure WEB3_RPC_URL",
            "checked_at": datetime.now(timezone.utc).isoformat() + "Z",
        }

    # ------------------------------------------------------------------
    # Smart contract registry
    # ------------------------------------------------------------------

    def register_contract(
        self,
        address: str,
        network: str,
        name: str,
        abi_functions: list[str] | None = None,
    ) -> ContractInfo:
        """Register a smart contract for monitoring."""
        contract = ContractInfo(
            address=address,
            network=network,
            name=name,
            abi_summary=abi_functions or [],
        )
        self._contracts[f"{network}:{address}"] = contract
        return contract

    def list_contracts(self) -> list[ContractInfo]:
        return list(self._contracts.values())

    # ------------------------------------------------------------------
    # AI-powered analysis
    # ------------------------------------------------------------------

    def analyse_defi_opportunity(
        self, protocol: str, tvl_usd: float, apy: float, risk_level: str
    ) -> Web3Report:
        """Use AI to analyse a DeFi investment opportunity."""
        if self._api_key:
            summary, recommendations = self._llm_defi_analysis(protocol, tvl_usd, apy, risk_level)
        else:
            summary, recommendations = self._placeholder_defi_analysis(protocol, tvl_usd, apy, risk_level)

        return Web3Report(
            network="defi",
            analysis_type="defi_opportunity",
            summary=summary,
            details={
                "protocol": protocol,
                "tvl_usd": tvl_usd,
                "apy": apy,
                "risk_level": risk_level,
            },
            recommendations=recommendations,
        )

    def generate_web3_integration_guide(self, repo_name: str, language: str = "Python") -> str:
        """Generate a Web3 integration guide for a repository."""
        if self._api_key:
            return self._llm_integration_guide(repo_name, language)
        return self._placeholder_integration_guide(repo_name, language)

    def get_network_summary(self) -> dict[str, Any]:
        """Return a summary of all supported networks and connection status."""
        return {
            "supported_networks": [
                {
                    "name": net.name,
                    "chain_id": net.chain_id,
                    "native_token": net.native_token,
                    "explorer": net.explorer_url,
                }
                for net in SUPPORTED_NETWORKS.values()
            ],
            "connected": self.is_connected(),
            "registered_contracts": len(self._contracts),
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _llm_defi_analysis(
        self, protocol: str, tvl_usd: float, apy: float, risk_level: str
    ) -> tuple[str, list[str]]:
        prompt = (
            f"Analyse this DeFi opportunity as an AI financial analyst:\n"
            f"Protocol: {protocol}\nTVL: ${tvl_usd:,.0f}\nAPY: {apy:.1f}%\n"
            f"Risk level: {risk_level}\n\n"
            "Provide: 1) A 2-sentence summary, 2) 3 actionable recommendations.\n"
            "Format as JSON: {\"summary\": \"\", \"recommendations\": []}"
        )
        try:
            raw = self._call_llm(prompt)
            import json
            data = json.loads(raw)
            return data.get("summary", ""), data.get("recommendations", [])
        except Exception:
            return self._placeholder_defi_analysis(protocol, tvl_usd, apy, risk_level)

    def _placeholder_defi_analysis(
        self, protocol: str, tvl_usd: float, apy: float, risk_level: str
    ) -> tuple[str, list[str]]:
        summary = (
            f"{protocol} offers {apy:.1f}% APY with ${tvl_usd:,.0f} TVL and {risk_level} risk. "
            "Configure an LLM API key for AI-powered analysis."
        )
        recommendations = [
            "Set OPENAI_API_KEY for AI-powered DeFi analysis",
            f"Research {protocol} smart contract audits before investing",
            "Diversify across multiple DeFi protocols to manage risk",
        ]
        return summary, recommendations

    def _llm_integration_guide(self, repo_name: str, language: str) -> str:
        prompt = (
            f"Write a concise Web3 integration guide for the GitHub repository '{repo_name}' "
            f"using {language}. Include: setup, connecting to Ethereum, reading contract data, "
            "and sending transactions. Use code examples."
        )
        return self._call_llm(prompt)

    def _placeholder_integration_guide(self, repo_name: str, language: str) -> str:
        return (
            f"# Web3 Integration Guide for {repo_name}\n\n"
            f"Language: {language}\n\n"
            "## Setup\n```bash\npip install web3\n```\n\n"
            "## Connect to Ethereum\n"
            "```python\nfrom web3 import Web3\n"
            "w3 = Web3(Web3.HTTPProvider('https://cloudflare-eth.com'))\n"
            "print(w3.is_connected())\n```\n\n"
            "Set WEB3_RPC_URL and OPENAI_API_KEY for full AI-powered guidance."
        )

    def _call_llm(self, prompt: str) -> str:
        if self._provider == "anthropic":
            import anthropic  # type: ignore[import]
            client = anthropic.Anthropic(api_key=self._api_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        else:
            import openai  # type: ignore[import]
            client = openai.OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            return response.choices[0].message.content or ""
