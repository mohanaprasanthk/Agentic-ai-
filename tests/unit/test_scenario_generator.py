import pytest

from one_credit import ScenarioGenerator, ScenarioGeneratorConfig
from one_credit.simulation import SimulationEngine


@pytest.fixture
def generator():
    return ScenarioGenerator(ScenarioGeneratorConfig(random_seed=7))


def test_scenario_generator_creation():
    maker = ScenarioGenerator()
    assert isinstance(maker, ScenarioGenerator)


def test_configuration_creation_and_validation():
    config = ScenarioGeneratorConfig(
        number_of_agents=12,
        number_of_resources=4,
        number_of_requests=7,
        conflict_probability=0.3,
        priority_range=("low", "critical"),
        flexibility_range=(2, 6),
        time_range=(2, 9),
        random_seed=11,
    )

    assert config.number_of_agents == 12
    assert config.number_of_resources == 4
    assert config.number_of_requests == 7
    assert config.conflict_probability == 0.3


def test_small_scenario_generation(generator):
    scenario = generator.generate_small()
    assert len(scenario.agents) == 5
    assert len(scenario.resources) == 3
    assert len(scenario.requests) == 5


def test_medium_scenario_generation(generator):
    scenario = generator.generate_medium()
    assert len(scenario.agents) == 10
    assert len(scenario.resources) == 5
    assert len(scenario.requests) == 10


def test_large_scenario_generation(generator):
    scenario = generator.generate_large()
    assert len(scenario.agents) == 25
    assert len(scenario.resources) == 10
    assert len(scenario.requests) == 25


def test_stress_scenario_generation(generator):
    scenario = generator.generate_stress()
    assert len(scenario.agents) == 50
    assert len(scenario.resources) == 20
    assert len(scenario.requests) == 50


def test_very_large_scenario_generation(generator):
    scenario = generator.generate_very_large()
    assert len(scenario.agents) == 100
    assert len(scenario.resources) == 30
    assert len(scenario.requests) == 100


def test_configurable_agent_count(generator):
    scenario = generator.generate(ScenarioGeneratorConfig(number_of_agents=7, number_of_resources=3, number_of_requests=6, random_seed=9))
    assert len(scenario.agents) == 7


def test_configurable_resource_and_request_count(generator):
    scenario = generator.generate(ScenarioGeneratorConfig(number_of_agents=6, number_of_resources=8, number_of_requests=12, random_seed=21))
    assert len(scenario.resources) == 8
    assert len(scenario.requests) == 12


def test_unique_ids_and_valid_references(generator):
    scenario = generator.generate_small()

    assert len({agent.id for agent in scenario.agents}) == len(scenario.agents)
    assert len({resource.id for resource in scenario.resources}) == len(scenario.resources)
    assert len({request.id for request in scenario.requests}) == len(scenario.requests)

    agent_ids = {agent.id for agent in scenario.agents}
    resource_names = {resource.name for resource in scenario.resources}
    for request in scenario.requests:
        assert request.requester_id in agent_ids
        assert set(request.required_resources).issubset(resource_names)


def test_conflict_probability_behavior(generator):
    low = generator.generate(ScenarioGeneratorConfig(number_of_agents=8, number_of_resources=2, number_of_requests=6, conflict_probability=0.0, random_seed=5))
    high = generator.generate(ScenarioGeneratorConfig(number_of_agents=8, number_of_resources=2, number_of_requests=6, conflict_probability=1.0, random_seed=5))

    assert len({request.requester_id for request in low.requests}) >= 1
    assert len({request.requester_id for request in high.requests}) >= 1
    assert low.requests[0].required_resources != high.requests[0].required_resources or low.requests[0].requester_id != high.requests[0].requester_id


def test_priority_range_and_metadata_values(generator):
    scenario = generator.generate(ScenarioGeneratorConfig(number_of_agents=5, number_of_resources=3, number_of_requests=4, priority_range=("normal", "high"), flexibility_range=(3, 8), time_range=(1, 5), random_seed=3))

    priorities = {request.priority for request in scenario.requests}
    assert priorities.issubset({"normal", "medium", "high"})
    for request in scenario.requests:
        assert 3 <= request.metadata["flexibility"] <= 8
        assert 1 <= request.metadata["timeline"] <= 5


def test_same_seed_produces_identical_scenario(generator):
    first = generator.generate(ScenarioGeneratorConfig(number_of_agents=9, number_of_resources=4, number_of_requests=8, random_seed=123))
    second = ScenarioGenerator(ScenarioGeneratorConfig(number_of_agents=9, number_of_resources=4, number_of_requests=8, random_seed=123)).generate()

    assert first.model_dump() == second.model_dump()


def test_different_seeds_produce_different_scenarios(generator):
    first = generator.generate(ScenarioGeneratorConfig(number_of_agents=9, number_of_resources=4, number_of_requests=8, random_seed=123))
    second = ScenarioGenerator(ScenarioGeneratorConfig(number_of_agents=9, number_of_resources=4, number_of_requests=8, random_seed=456)).generate()

    assert first.model_dump() != second.model_dump()


def test_generated_scenario_is_valid_for_simulation_engine(generator):
    scenario = generator.generate_medium()
    engine = SimulationEngine()
    assert engine.validate_scenario(scenario) is True


def test_same_generated_scenario_works_across_architectures(generator):
    scenario = generator.generate(ScenarioGeneratorConfig(number_of_agents=8, number_of_resources=4, number_of_requests=6, random_seed=77))
    engine = SimulationEngine()

    for architecture in [
        "CENTRALIZED",
        "HIERARCHICAL",
        "DECENTRALIZED",
        "SEQUENTIAL",
        "PARALLEL",
        "BLACKBOARD",
        "PEER_TO_PEER",
    ]:
        result = engine.run(scenario, architecture=architecture)
        assert result.architecture == architecture
        assert isinstance(result, type(result))


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        ScenarioGeneratorConfig(number_of_agents=0)

    with pytest.raises(ValueError):
        ScenarioGeneratorConfig(conflict_probability=1.5)

    with pytest.raises(ValueError):
        ScenarioGeneratorConfig(priority_range=("low", "bad"))


def test_deterministic_generation_is_reproducible_for_seeded_runs():
    config = ScenarioGeneratorConfig(number_of_agents=6, number_of_resources=3, number_of_requests=5, random_seed=99)
    first = ScenarioGenerator(config).generate()
    second = ScenarioGenerator(config).generate()
    assert first.model_dump() == second.model_dump()
