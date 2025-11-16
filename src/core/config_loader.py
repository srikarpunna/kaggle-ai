"""
ElderCare Agent - Configuration Loader
Loads all YAML configuration files and provides structured access.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    name: str
    description: str
    model: str
    temperature: float
    max_tokens: int
    role: str
    capabilities: List[str]
    tools: List[str]
    routes_to: Optional[List[str]] = None
    platforms: Optional[Dict[str, Any]] = None
    templates: Optional[List[str]] = None
    accessibility: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None


@dataclass
class TaskConfig:
    """Configuration for a task."""
    name: str
    description: str
    category: str
    priority: str
    intent_patterns: List[str]
    required_information: List[str]
    optional_information: List[str]
    agent_workflow: List[Dict[str, Any]]
    success_criteria: Dict[str, Any]
    ui_template: str
    examples: List[Dict[str, Any]]


@dataclass
class UITemplateConfig:
    """Configuration for a UI template."""
    name: str
    description: str
    accessibility_level: str
    layout: Dict[str, Any]
    elements: List[Dict[str, Any]]
    animations: Dict[str, Any]
    auto_cleanup: Optional[Dict[str, Any]] = None
    example_data: Optional[Dict[str, Any]] = None


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    description: str
    port: int
    transport: str
    tools: List[Dict[str, Any]]
    storage: Dict[str, Any]


class ConfigLoader:
    """Loads and provides access to all configuration files."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)

        if not self.config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {self.config_dir}")

        self.agents: Dict[str, AgentConfig] = {}
        self.tasks: Dict[str, TaskConfig] = {}
        self.prompts: Dict[str, Dict[str, str]] = {}
        self.ui_templates: Dict[str, UITemplateConfig] = {}
        self.mcp_servers: Dict[str, MCPServerConfig] = {}

        self._load_all()

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML file."""
        filepath = self.config_dir / filename
        logger.info(f"Loading config file: {filepath}")

        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            return data
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            raise

    def _load_all(self):
        """Load all configuration files."""
        logger.info("Loading all configurations...")

        self._load_agents()
        self._load_tasks()
        self._load_prompts()
        self._load_ui_templates()
        self._load_mcp_servers()

        logger.info("All configurations loaded successfully")

    def _load_agents(self):
        """Load agent configurations."""
        data = self._load_yaml("agents.yaml")
        agents_data = data.get("agents", {})

        for agent_id, agent_data in agents_data.items():
            self.agents[agent_id] = AgentConfig(
                name=agent_data.get("name"),
                description=agent_data.get("description"),
                model=agent_data.get("model"),
                temperature=agent_data.get("temperature"),
                max_tokens=agent_data.get("max_tokens"),
                role=agent_data.get("role"),
                capabilities=agent_data.get("capabilities", []),
                tools=agent_data.get("tools", []),
                routes_to=agent_data.get("routes_to"),
                platforms=agent_data.get("platforms"),
                templates=agent_data.get("templates"),
                accessibility=agent_data.get("accessibility"),
                storage=agent_data.get("storage")
            )

        logger.info(f"Loaded {len(self.agents)} agent configurations")

    def _load_tasks(self):
        """Load task configurations."""
        data = self._load_yaml("tasks.yaml")
        tasks_data = data.get("tasks", {})

        for task_id, task_data in tasks_data.items():
            self.tasks[task_id] = TaskConfig(
                name=task_data.get("name"),
                description=task_data.get("description"),
                category=task_data.get("category"),
                priority=task_data.get("priority"),
                intent_patterns=task_data.get("intent_patterns", []),
                required_information=task_data.get("required_information", []),
                optional_information=task_data.get("optional_information", []),
                agent_workflow=task_data.get("agent_workflow", []),
                success_criteria=task_data.get("success_criteria", {}),
                ui_template=task_data.get("ui_template"),
                examples=task_data.get("examples", [])
            )

        logger.info(f"Loaded {len(self.tasks)} task configurations")

    def _load_prompts(self):
        """Load prompt templates."""
        data = self._load_yaml("prompts.yaml")

        # Load system prompts
        self.prompts["system"] = data.get("system_prompts", {})

        # Load task-specific prompts
        self.prompts["tasks"] = data.get("task_prompts", {})

        # Load error prompts
        self.prompts["errors"] = data.get("error_prompts", {})

        # Load conversation prompts
        self.prompts["conversation"] = data.get("conversation_prompts", {})

        # Load multi-turn prompts
        self.prompts["multi_turn"] = data.get("multi_turn", {})

        logger.info("Loaded prompt templates")

    def _load_ui_templates(self):
        """Load UI template configurations."""
        data = self._load_yaml("ui_templates.yaml")
        templates_data = data.get("templates", {})

        for template_id, template_data in templates_data.items():
            self.ui_templates[template_id] = UITemplateConfig(
                name=template_data.get("name"),
                description=template_data.get("description"),
                accessibility_level=template_data.get("accessibility_level"),
                layout=template_data.get("layout", {}),
                elements=template_data.get("elements", []),
                animations=template_data.get("animations", {}),
                auto_cleanup=template_data.get("auto_cleanup"),
                example_data=template_data.get("example_data")
            )

        logger.info(f"Loaded {len(self.ui_templates)} UI templates")

    def _load_mcp_servers(self):
        """Load MCP server configurations."""
        data = self._load_yaml("mcp_servers.yaml")
        servers_data = data.get("mcp_servers", {})

        for server_id, server_data in servers_data.items():
            self.mcp_servers[server_id] = MCPServerConfig(
                name=server_data.get("name"),
                description=server_data.get("description"),
                port=server_data.get("port"),
                transport=server_data.get("transport"),
                tools=server_data.get("tools", []),
                storage=server_data.get("storage", {})
            )

        logger.info(f"Loaded {len(self.mcp_servers)} MCP server configurations")

    def get_agent_config(self, agent_id: str) -> AgentConfig:
        """Get configuration for a specific agent."""
        if agent_id not in self.agents:
            raise KeyError(f"Agent configuration not found: {agent_id}")
        return self.agents[agent_id]

    def get_task_config(self, task_id: str) -> TaskConfig:
        """Get configuration for a specific task."""
        if task_id not in self.tasks:
            raise KeyError(f"Task configuration not found: {task_id}")
        return self.tasks[task_id]

    def get_prompt(self, category: str, *path, **kwargs) -> str:
        """
        Get a prompt template and format it with provided kwargs.

        Args:
            category: Prompt category (system, tasks, errors, conversation, multi_turn)
            *path: One or more path components to navigate nested prompts
            **kwargs: Variables to format the prompt with

        Returns:
            Formatted prompt string
        """
        if category not in self.prompts:
            raise KeyError(f"Prompt category not found: {category}")

        # Navigate through nested structure
        template = self.prompts[category]
        full_path = [category] + list(path)
        
        for i, key in enumerate(path):
            if isinstance(template, dict):
                if key not in template:
                    raise KeyError(f"Prompt not found: {'.'.join(full_path[:i+2])}")
                template = template[key]
            else:
                raise KeyError(f"Cannot navigate deeper: {'.'.join(full_path[:i+1])} is not a dict")

        if not isinstance(template, str):
            raise KeyError(f"Prompt path {'.'.join(full_path)} does not point to a string template")

        # Format the template with provided kwargs
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing variable in prompt template: {e}")
            return template

    def get_ui_template(self, template_id: str) -> UITemplateConfig:
        """Get configuration for a specific UI template."""
        if template_id not in self.ui_templates:
            raise KeyError(f"UI template not found: {template_id}")
        return self.ui_templates[template_id]

    def get_mcp_server_config(self, server_id: str) -> MCPServerConfig:
        """Get configuration for a specific MCP server."""
        if server_id not in self.mcp_servers:
            raise KeyError(f"MCP server configuration not found: {server_id}")
        return self.mcp_servers[server_id]

    def list_agents(self) -> List[str]:
        """Get list of all available agent IDs."""
        return list(self.agents.keys())

    def list_tasks(self) -> List[str]:
        """Get list of all available task IDs."""
        return list(self.tasks.keys())

    def list_ui_templates(self) -> List[str]:
        """Get list of all available UI template IDs."""
        return list(self.ui_templates.keys())

    def list_mcp_servers(self) -> List[str]:
        """Get list of all available MCP server IDs."""
        return list(self.mcp_servers.keys())


# Global config instance
_config: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ConfigLoader()
    return _config


def load_user_profile(user_id: str, data_dir: str = "data/users") -> Dict[str, Any]:
    """Load a user profile YAML file."""
    user_file = Path(data_dir) / f"{user_id}.yaml"

    if not user_file.exists():
        raise FileNotFoundError(f"User profile not found: {user_file}")

    with open(user_file, 'r') as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test config loading
    print("Loading configurations...")
    config = ConfigLoader()

    print(f"\n✓ Loaded {len(config.agents)} agents:")
    for agent_id in config.list_agents():
        agent = config.get_agent_config(agent_id)
        print(f"  - {agent.name}")

    print(f"\n✓ Loaded {len(config.tasks)} tasks:")
    for task_id in config.list_tasks():
        task = config.get_task_config(task_id)
        print(f"  - {task.name}")

    print(f"\n✓ Loaded {len(config.ui_templates)} UI templates:")
    for template_id in config.list_ui_templates():
        template = config.get_ui_template(template_id)
        print(f"  - {template.name}")

    print(f"\n✓ Loaded {len(config.mcp_servers)} MCP servers:")
    for server_id in config.list_mcp_servers():
        server = config.get_mcp_server_config(server_id)
        print(f"  - {server.name}")

    # Test prompt loading
    print("\n✓ Testing prompt retrieval:")
    greeting = config.get_prompt("conversation", "greeting",
                                  time_of_day="morning",
                                  user_name="Margaret")
    print(f"  Greeting prompt length: {len(greeting)} chars")

    print("\n✓ Configuration system working correctly!")
