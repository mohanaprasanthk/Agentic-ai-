from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from one_credit.api.schemas import HealthResponse
from one_credit.api.store import store
from one_credit.architecture_comparison import ArchitectureComparisonEngine
from one_credit.metrics import MetricsEngine
from one_credit.models import Agent, Resource
from one_credit.simulation import ArchitectureType, Scenario, SimulationEngine


def create_app() -> FastAPI:
    app = FastAPI(
        title="One Credit API",
        version="0.1.0",
        description="REST API for agent, resource, simulation, metrics, and architecture comparison workflows.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:4173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _validate_scenario_payload(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Scenario payload must be a JSON object.")

        data = dict(payload)
        if "scenario" in data and isinstance(data["scenario"], dict):
            data = dict(data["scenario"])
        elif "scenario" in data and isinstance(data["scenario"], Scenario):
            return data["scenario"].model_dump()

        if "architecture" in payload and "architecture" not in data:
            data["architecture"] = payload["architecture"]
        if "parameters" in payload and "parameters" not in data and "simulation_parameters" not in data:
            data["parameters"] = payload["parameters"]

        architecture_value = data.get("architecture", ArchitectureType.CENTRALIZED)
        normalized = str(architecture_value).strip().upper()
        allowed = {"CENTRALIZED", "HIERARCHICAL", "DECENTRALIZED", "SEQUENTIAL", "PARALLEL", "BLACKBOARD", "PEER_TO_PEER"}
        if normalized not in allowed:
            raise ValueError(f"Invalid architecture: {architecture_value}")

        agents = data.get("agents") or []
        resources = data.get("resources") or []
        requests = data.get("requests") or []
        if not agents:
            raise ValueError("Scenario must include at least one agent.")
        if not resources:
            raise ValueError("Scenario must include at least one resource.")
        if not requests:
            raise ValueError("Scenario must include at least one request.")

        agent_ids = {entry.get("id") for entry in agents if isinstance(entry, dict) and entry.get("id")}
        resource_names = {entry.get("name") for entry in resources if isinstance(entry, dict) and entry.get("name")}
        for request_entry in requests:
            if not isinstance(request_entry, dict):
                raise ValueError("Each request must be an object.")
            requester_id = request_entry.get("requester_id")
            if not requester_id:
                raise ValueError(f"Request {request_entry.get('id', 'unknown')} is missing requester_id.")
            if requester_id not in agent_ids:
                raise ValueError(f"Request {request_entry.get('id', 'unknown')} references unknown requester_id {requester_id}.")
            required = request_entry.get("required_resources") or []
            missing = [item for item in required if item not in resource_names]
            if missing:
                raise ValueError(f"Request {request_entry.get('id', 'unknown')} references missing resources: {missing}")
        return data

    def _coerce_scenario(payload: Any) -> Scenario:
        scenario_data = _validate_scenario_payload(payload)
        if isinstance(scenario_data, Scenario):
            return scenario_data
        return Scenario.model_validate(scenario_data)

    @app.get("/", response_model=HealthResponse, tags=["health"])
    async def root() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/agents", response_model=list[Agent], tags=["agents"])
    async def list_agents() -> list[Agent]:
        return store.list_agents()

    @app.post("/api/agents", response_model=Agent, status_code=status.HTTP_201_CREATED, tags=["agents"])
    async def create_agent(agent: Agent) -> Agent:
        return store.register_agent(agent)

    @app.get("/api/resources", response_model=list[Resource], tags=["resources"])
    async def list_resources() -> list[Resource]:
        return store.list_resources()

    @app.post("/api/resources", response_model=Resource, status_code=status.HTTP_201_CREATED, tags=["resources"])
    async def create_resource(resource: Resource) -> Resource:
        return store.register_resource(resource)

    @app.post("/api/simulation/run", response_model=dict[str, Any], tags=["simulation"])
    async def run_simulation(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            scenario = _coerce_scenario(payload)
            if "architecture" in payload and isinstance(payload["architecture"], (str, ArchitectureType)):
                scenario = Scenario.model_validate({**scenario.model_dump(), "architecture": payload["architecture"]})
            result = SimulationEngine().run(scenario)
            store.store_simulation(result)
            return result.model_dump()
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/simulation/{simulation_id}", response_model=dict[str, Any], tags=["simulation"])
    async def get_simulation_result(simulation_id: str) -> dict[str, Any]:
        result = store.get_simulation(simulation_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown simulation ID: {simulation_id}")
        return result.model_dump()

    @app.get("/api/simulation/{simulation_id}/metrics", response_model=dict[str, Any], tags=["simulation"])
    async def get_simulation_metrics(simulation_id: str) -> dict[str, Any]:
        result = store.get_simulation(simulation_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown simulation ID: {simulation_id}")
        metrics = MetricsEngine().calculate(result)
        store.store_metrics(simulation_id, metrics)
        return metrics.model_dump()

    @app.post("/api/comparison/run", response_model=dict[str, Any], tags=["comparison"])
    async def run_comparison(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            scenario = _coerce_scenario(payload)
            comparison = ArchitectureComparisonEngine().compare(scenario)
            store.store_comparison(comparison)
            return comparison.model_dump()
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return app


app = create_app()

__all__ = ["app", "create_app"]
