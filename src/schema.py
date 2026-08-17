# Pydantic v2 schema for a single app's research result. All fields have safe defaults so partial results never crash.
from pydantic import BaseModel, Field


class AppResearch(BaseModel):
    app_name: str = Field(default="", description="Name of the app being researched")
    category: str = Field(default="unknown", description="One of the 10 app categories")
    one_liner: str = Field(default="", description="One line on what the app does")
    auth_method: str = Field(default="unknown", description="e.g. OAuth2, API key, Basic, token, other")
    access_type: str = Field(default="unknown", description="One of: self-serve, gated, unknown")
    api_surface: str = Field(default="unknown", description="REST / GraphQL / none, plus rough breadth")
    has_mcp: bool = Field(default=False, description="Whether a known official MCP server exists")
    buildability: str = Field(default="unknown", description="One of: buildable-now, needs-outreach, blocked, unknown")
    main_blocker: str = Field(default="", description="Biggest blocker if not buildable now; empty if none")
    evidence_url: str = Field(default="", description="Docs/article URL supporting the answer")
    confidence: str = Field(default="low", description="Model self-confidence: high / medium / low")
    researched_by: str = Field(default="", description="Model that produced the row, e.g. qwen2.5:7b")
