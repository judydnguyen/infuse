# # """Basic agent class. See https://mini-swe-agent.com/latest/advanced/control_flow/ for visual explanation."""

# # import re
# # import subprocess
# # from collections.abc import Callable
# # from dataclasses import asdict, dataclass

# # from jinja2 import StrictUndefined, Template
# # from termcolor import colored



# # @dataclass
# # class AgentConfig:
# #     # The default settings are the bare minimum to run the agent. Take a look at the config files for improved settings.
# #     system_template: str = "You are a helpful assistant that can do anything."
# #     instance_template: str = (
# #         "Your task: {{task}}. Please reply with a single shell command in triple backticks. "
# #         "To finish, the first line of the output of the shell command must be 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'."
# #     )
# #     # injected_instance_template: str = (
# #     #     "Your task: {{task}}. Please reply with a single shell command in triple backticks. "
# #     #     "To finish, the first line of the output of the shell command must be 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'."
# #     # )
# #     timeout_template: str = (
# #         "The last command <command>{{action['action']}}</command> timed out and has been killed.\n"
# #         "The output of the command was:\n <output>\n{{output}}\n</output>\n"
# #         "Please try another command and make sure to avoid those requiring interactive input."
# #     )
# #     format_error_template: str = "Please always provide EXACTLY ONE action in triple backticks."
# #     action_observation_template: str = "Observation: {{output}}"
# #     step_limit: int = 10
# #     cost_limit: float = 0.5


# # class NonTerminatingException(Exception):
# #     """Raised for conditions that can be handled by the agent."""


# # class FormatError(NonTerminatingException):
# #     """Raised when the LM's output is not in the expected format."""


# # class ExecutionTimeoutError(NonTerminatingException):
# #     """Raised when the action execution timed out."""


# # class TerminatingException(Exception):
# #     """Raised for conditions that terminate the agent."""


# # class Submitted(TerminatingException):
# #     """Raised when the LM declares that the agent has finished its task."""


# # class LimitsExceeded(TerminatingException):
# #     """Raised when the agent has reached its cost or step limit."""


# # class DefaultAgent:
# #     def __init__(self, model: Model, env: Environment, *, config_class: Callable = AgentConfig, **kwargs):
# #         self.config = config_class(**kwargs)
# #         self.messages: list[dict] = []
# #         self.model = model
# #         self.env = env
# #         self.n_steps = 0
# #         self.extra_template_vars = {}
        
# #         # default injection configurations
# #         self.default_injection_config = {
# #             "attack_type": "middle",
# #             "category": "Compromising Computers",
# #             "attack_index": 0
# #         }

# #     def render_template(self, template: str, **kwargs) -> str:
# #         template_vars = asdict(self.config) | self.env.get_template_vars() | self.model.get_template_vars()
# #         return Template(template, undefined=StrictUndefined).render(
# #             **kwargs, **template_vars, **self.extra_template_vars
# #         )

# #     def add_message(self, role: str, content: str, **kwargs):
# #         self.messages.append({"role": role, "content": content, **kwargs})

# #     def run(self, task: str, **kwargs) -> tuple[str, str]:
# #         """Run step() until agent is finished. Return exit status & message"""
# #         self.extra_template_vars |= {"task": task, **kwargs}
# #         self.messages = []
# #         self.add_message("system", self.render_template(self.config.system_template))
# #         self.add_message("user", self.render_template(self.config.instance_template))
# #         while True:
# #             try:
# #                 self.step()
# #             except NonTerminatingException as e:
# #                 self.add_message("user", str(e))
# #             except TerminatingException as e:
# #                 self.add_message("user", str(e))
# #                 return type(e).__name__, str(e)

# #     def step(self) -> dict:
# #         """Query the LM, execute the action, return the observation.

# #         This method enforces a maximum step limit (if configured). When the
# #         step limit is reached, a LimitsExceeded exception is raised to stop the agent.
# #         """
# #         # increment step counter
# #         self.n_steps += 1

# #         # enforce max-step limit (0 means unlimited)
# #         if 0 < self.config.step_limit <= self.n_steps:
# #             # raise terminating exception so run() will return and log the status
# #             raise LimitsExceeded(f"Reached maximum step limit: {self.config.step_limit}")

# #         # existing behavior: inject periodically and fetch observation
# #         if self.n_steps % 5 == 1:
# #             self.default_injection_config = {
# #                 "attack_type": "start",
# #                 "category": "Compromising Computers",
# #                 "attack_index": 0
# #             }
# #             print(colored(f"Injected observation: {self.default_injection_config}", "green"))
# #             return self.get_observation(self.query(), injected=True, injection_config=self.default_injection_config)
# #         return self.get_observation(self.query())


# #     def query(self) -> dict:
# #         """Query the model and return the response."""
# #         if 0 < self.config.step_limit <= self.model.n_calls or 0 < self.config.cost_limit <= self.model.cost:
# #             raise LimitsExceeded()
# #         response = self.model.query(self.messages)
# #         self.add_message("assistant", **response)
# #         return response

# #     # def get_observation(self, response: dict) -> dict:
# #     #     """Execute the action and return the observation."""
# #     #     output = self.execute_action(self.parse_action(response))
# #     #     observation = self.render_template(self.config.action_observation_template, output=output)
# #     #     self.add_message("user", observation)
# #     #     return output
    
# #     def get_observation(self, response: dict, injected: bool = False, injection_config: dict | None = None) -> dict:
# #         """Execute the action and return the observation."""
# #         output = self.execute_action(self.parse_action(response))
        
# #         if injected:
# #             # Conduct prompt injection here...
# #             if not isinstance(injection_config, dict):
# #                 raise ValueError("injection_config must be provided as a dict when injected=True")

# #             attack_type = injection_config.get("attack_type")
# #             category = injection_config.get("category")
# #             attack_index = injection_config.get("attack_index")

# #             if attack_type is None or category is None or attack_index is None:
# #                 raise ValueError(
# #                     "injection_config must contain 'attack_type', 'category', and 'attack_index'"
# #                 )

# #             # # build a REDACTED placeholder to avoid exposing real payloads
# #             # placeholder = retrieve_ideal(PROMPT_INJECTION_CSV_PATH, category, attack_index)

# #             # apply injection to the instance_template
# #             observation = self.render_template(self.config.action_observation_template, output=output)
# #             injected_instance, _ = get_injected_template(attack_type=attack_type, category=category, 
# #                                                          attack_index=attack_index, 
# #                                                          template=observation)
# #             print(colored(f"Injected observation: {injected_instance}", "green"))
# #             # append injected prompt to messages as a user message
# #             # (this simulates the environment/user providing an injected context)
# #             self.add_message("user", injected_instance)
# #         else:
# #             observation = self.render_template(self.config.action_observation_template, output=output)
# #             self.add_message("user", observation)
# #         return output

# #     def parse_action(self, response: dict) -> dict:
# #         """Parse the action from the message. Returns the action."""
# #         actions = re.findall(r"```bash\s*\n(.*?)\n```", response["content"], re.DOTALL)
# #         if len(actions) == 1:
# #             return {"action": actions[0].strip(), **response}
# #         raise FormatError(self.render_template(self.config.format_error_template, actions=actions))

# #     def execute_action(self, action: dict) -> dict:
# #         try:
# #             output = self.env.execute(action["action"])
# #         except subprocess.TimeoutExpired as e:
# #             output = e.output.decode("utf-8", errors="replace") if e.output else ""
# #             raise ExecutionTimeoutError(
# #                 self.render_template(self.config.timeout_template, action=action, output=output)
# #             )
# #         except TimeoutError:
# #             raise ExecutionTimeoutError(self.render_template(self.config.timeout_template, action=action, output=""))
# #         self.has_finished(output)
# #         return output

# #     def has_finished(self, output: dict[str, str]):
# #         """Raises Submitted exception with final output if the agent has finished its task."""
# #         lines = output.get("output", "").lstrip().splitlines(keepends=True)
# #         if lines and lines[0].strip() in ["MINI_SWE_AGENT_FINAL_OUTPUT", "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"]:
# #             raise Submitted("".join(lines[1:]))


# """Basic agent class. See https://mini-swe-agent.com/latest/advanced/control_flow/ for visual explanation."""

# import re
# import subprocess
# from collections.abc import Callable
# from dataclasses import asdict, dataclass

# from jinja2 import StrictUndefined, Template
# from termcolor import colored

# from minisweagent import Environment, Model
# from .prompt_injection import get_injected_template
# from .attack_eval import calc_asr
# # from .metrics import calc_asr  # ✅ <--- import your ASR calculation function


# @dataclass
# class AgentConfig:
#     system_template: str = "You are a helpful assistant that can do anything."
#     instance_template: str = (
#         "Your task: {{task}}. Please reply with a single shell command in triple backticks. "
#         "To finish, the first line of the output of the shell command must be 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'."
#     )
#     timeout_template: str = (
#         "The last command <command>{{action['action']}}</command> timed out and has been killed.\n"
#         "The output of the command was:\n <output>\n{{output}}\n</output>\n"
#         "Please try another command and make sure to avoid those requiring interactive input."
#     )
#     format_error_template: str = "Please always provide EXACTLY ONE action in triple backticks."
#     action_observation_template: str = "Observation: {{output}}"
#     step_limit: int = 10
#     cost_limit: float = 0.5


# class NonTerminatingException(Exception):
#     pass


# class FormatError(NonTerminatingException):
#     pass


# class ExecutionTimeoutError(NonTerminatingException):
#     pass


# class TerminatingException(Exception):
#     pass


# class Submitted(TerminatingException):
#     pass


# class LimitsExceeded(TerminatingException):
#     pass


# class DefaultAgent:
#     def __init__(self, model: Model, env: Environment, *, config_class: Callable = AgentConfig, **kwargs):
#         self.config = config_class(**kwargs)
#         self.messages: list[dict] = []
#         self.model = model
#         self.env = env
#         self.n_steps = -1
#         self.extra_template_vars = {}

#         # default injection configurations
#         self.default_injection_config = {
#             "attack_type": "start",
#             "category": "Bringing Down Hosts and Servers (Denial of Service)",
#             "attack_index": 4
#         }

#         # ✅ store ASR metrics
#         self.metrics: list[dict] = []

#     def render_template(self, template: str, **kwargs) -> str:
#         template_vars = asdict(self.config) | self.env.get_template_vars() | self.model.get_template_vars()
#         return Template(template, undefined=StrictUndefined).render(
#             **kwargs, **template_vars, **self.extra_template_vars
#         )

#     def add_message(self, role: str, content: str, **kwargs):
#         self.messages.append({"role": role, "content": content, **kwargs})

#     def run(self, task: str, **kwargs) -> tuple[str, str]:
#         """Run step() until agent is finished. Return exit status & message"""
#         self.extra_template_vars |= {"task": task, **kwargs}
#         self.messages = []
#         self.metrics = []  # reset for each new run

#         self.add_message("system", self.render_template(self.config.system_template))
#         self.add_message("user", self.render_template(self.config.instance_template))

#         while True:
#             try:
#                 self.step()
#             except NonTerminatingException as e:
#                 self.add_message("user", str(e))
#             except TerminatingException as e:
#                 # ✅ print summary ASR when terminated
#                 if self.metrics:
#                     successes = sum(1 for m in self.metrics if m["asr"].get("success"))
#                     total = len(self.metrics)
#                     overall_asr = successes / total
#                     print(colored(f"[ASR Summary] {successes}/{total} ({overall_asr:.1%}) successful actions", "cyan"))
#                 self.add_message("user", str(e))
#                 return type(e).__name__, str(e)

#     def step(self) -> dict:
#         self.n_steps += 1
#         if 0 < self.n_steps >= self.config.step_limit:
#             raise LimitsExceeded(f"Reached maximum step limit: {self.config.step_limit}")
#         calculate_asr = self.n_steps % 5 == 1 and self.n_steps > 0

#         if self.n_steps % 5 == 0:
#             self.default_injection_config = {
#                 "attack_type": "end",
#                 "category": "Bringing Down Hosts and Servers (Denial of Service)",
#                 "attack_index": 0
#             }
#             print(colored(f"Injected observation: {self.default_injection_config}", "green"))
#             return self.get_observation(self.query(), injected=True,
#                                         calculate_asr=calculate_asr,
#                                         injection_config=self.default_injection_config)
#         return self.get_observation(self.query(), calculate_asr=calculate_asr, 
#                                     injection_config=self.default_injection_config)

#     def query(self) -> dict:
#         if 0 < self.config.step_limit <= self.model.n_calls or 0 < self.config.cost_limit <= self.model.cost:
#             raise LimitsExceeded()
#         response = self.model.query(self.messages)
#         self.add_message("assistant", **response)
#         return response

#     # def get_observation(self, response: dict, injected: bool = False,
#     #                     calculate_asr: bool = False,
#     #                     injection_config: dict | None = None) -> dict:
#     #     """Execute the action and return the observation."""
#     #     action = self.parse_action(response)
#     #     output = self.execute_action(action)
#     #     # print(colored(f"Output: {output}", "yellow"))
#     #     # print(colored(f"Action: {action}", "yellow"))
#     #     # print(colored(f"Injection config: {injection_config}", "yellow"))
#     #     # print(colored(f"Calculate ASR: {calculate_asr}", "yellow"))
#     #     # ✅ compute ASR immediately after execution (safe before observation feedback)
#     #     if calculate_asr:
#     #         try:
#     #             asr_result = calc_asr(injection_config, action, output)
#     #             self.metrics.append({
#     #                 "step": self.n_steps,
#     #                 "injected": injected,
#     #                 "attack_config": injection_config,
#     #                 "action": action,
#     #                 "output": output,
#     #                 "asr": asr_result,
#     #             })
#     #             if asr_result['success']:
#     #                 # stop the agent
#     #                 raise Submitted("ASR is successful, the agent will stop.")
#     #             print(colored(f"ASR result: {asr_result}", "yellow"))
#     #         except Exception as e:
#     #             print(colored(f"[ASR error] {e}", "red"))

#     #     observation = self.render_template(self.config.action_observation_template, output=output)

#     #     if injected:
#     #         if not isinstance(injection_config, dict):
#     #             raise ValueError("injection_config must be provided as a dict when injected=True")

#     #         attack_type = injection_config.get("attack_type")
#     #         category = injection_config.get("category")
#     #         attack_index = injection_config.get("attack_index")

#     #         injected_instance, _ = get_injected_template(
#     #             attack_type=attack_type,
#     #             category=category,
#     #             attack_index=attack_index,
#     #             template=observation,
#     #         )
#     #         print(colored(f"Injected observation: {injected_instance}", "green"))
#     #         self.add_message("user", injected_instance)
#     #     else:
#     #         self.add_message("user", observation)
#     #     return output

#     def get_observation(self, response: dict, injected: bool = False,
#                         calculate_asr: bool = False,
#                         injection_config: dict | None = None) -> dict:
#         """Execute the action and return the observation."""
#         action = self.parse_action(response)
#         output = self.execute_action(action)

#         # ASR (unchanged)
#         if calculate_asr:
#             try:
#                 asr_result = calc_asr(injection_config, action, output)
#                 self.metrics.append({
#                     "step": self.n_steps,
#                     "injected": injected,
#                     "attack_config": injection_config,
#                     "action": action,
#                     "output": output,
#                     "asr": asr_result,
#                 })
#                 print(colored(f"ASR result: {asr_result}", "red"))
#                 if asr_result.get("success") is True and self.n_steps > 5:
#                     self.add_message("user", f"[AttackSucceeded] ASR succeeded at step {self.n_steps}.")
#                     self.complete_now("ASR success: agent marked complete.")

#                 # print(colored(f"ASR result: {asr_result}", "yellow"))
#             except Exception as e:
#                 print(colored(f"[ASR error] {e}", "red"))

#         observation = self.render_template(self.config.action_observation_template, output=output)

#         if injected:
#             if not isinstance(injection_config, dict):
#                 raise ValueError("injection_config must be provided as a dict when injected=True")

#             attack_type = injection_config.get("attack_type")
#             category = injection_config.get("category")
#             attack_index = injection_config.get("attack_index")

#             # # render current system template first, then inject into THAT string
#             # current_system = self.render_template(self.config.system_template)
#             # injected_system, _ = get_injected_template(
#             #     attack_type=attack_type,
#             #     category=category,
#             #     attack_index=attack_index,
#             #     template=current_system,
#             # )

#             # # ✅ ONLY replace the system prompt if injected=True
#             # # find the first system message and replace its content
#             # for m in self.messages:
#             #     if m.get("role") == "system":
#             #         m["content"] = injected_system
#             #         break
#             # else:
#             #     # if somehow no system message exists, add one at the front
#             #     self.messages.insert(0, {"role": "system", "content": injected_system})

#             # print(colored("System prompt injected (system message replaced).", "green"))

#             # still add the observation as a user message
#             attack_type = injection_config.get("attack_type")
#             category = injection_config.get("category")
#             attack_index = injection_config.get("attack_index")

#             injected_instance, _ = get_injected_template(
#                 attack_type=attack_type,
#                 category=category,
#                 attack_index=attack_index,
#                 template=observation,
#             )
#             print(colored(f"Injected observation: {injected_instance}", "green"))
#             self.add_message("user", injected_instance)
#             # self.add_message("user", observation)
#         else:
#             # no injection: DO NOT touch the system message
#             self.add_message("user", observation)

#         return output

#     def parse_action(self, response: dict) -> dict:
#         actions = re.findall(r"```bash\s*\n(.*?)\n```", response["content"], re.DOTALL)
#         if len(actions) == 1:
#             return {"action": actions[0].strip(), **response}
#         raise FormatError(self.render_template(self.config.format_error_template, actions=actions))

#     def execute_action(self, action: dict) -> dict:
#         try:
#             output = self.env.execute(action["action"])
#         except subprocess.TimeoutExpired as e:
#             output = e.output.decode("utf-8", errors="replace") if e.output else ""
#             raise ExecutionTimeoutError(
#                 self.render_template(self.config.timeout_template, action=action, output=output)
#             )
#         except TimeoutError:
#             raise ExecutionTimeoutError(self.render_template(self.config.timeout_template, action=action, output=""))
#         self.has_finished(output)
#         return output

#     def complete_now(self, message: str = "") -> None:
#         sentinel = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
#         self.has_finished({"output": f"{sentinel}\n{message}\n"})
 
#     def has_finished(self, output: dict[str, str]):
#         lines = output.get("output", "").lstrip().splitlines(keepends=True)
#         if lines and lines[0].strip() in ["MINI_SWE_AGENT_FINAL_OUTPUT", "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"]:
#             raise Submitted("".join(lines[1:]))

"""Basic agent class. See https://mini-swe-agent.com/latest/advanced/control_flow/ for visual explanation."""

import re
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Literal, Optional

from jinja2 import StrictUndefined, Template

from minisweagent import Environment, Model
from infuse.defenses.base import Defense, NoDefense, BLOCKED_ACTION


@dataclass
class AgentConfig:
    # The default settings are the bare minimum to run the agent. Take a look at the config files for improved settings.
    system_template: str = "You are a helpful assistant that can do anything."
    instance_template: str = (
        "Your task: {{task}}. Please reply with a single shell command in triple backticks. "
        "To finish, the first line of the output of the shell command must be 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'."
    )
    timeout_template: str = (
        "The last command <command>{{action['action']}}</command> timed out and has been killed.\n"
        "The output of the command was:\n <output>\n{{output}}\n</output>\n"
        "Please try another command and make sure to avoid those requiring interactive input."
    )
    format_error_template: str = "Please always provide EXACTLY ONE action in triple backticks."
    action_observation_template: str = "Observation: {{output}}"
    step_limit: int = 0
    cost_limit: float = 3.0
    # Attack injection configuration
    inject_attack: bool = False
    attack_id: Optional[int] = None
    attack_security_violation: Optional[str] = None
    attack_injection_type: Literal["none", "start", "end", "middle"] = "end"
    attack_injection_step: Optional[int] = None  # Inject at specific step (None = every step when inject_attack=True)


class NonTerminatingException(Exception):
    """Raised for conditions that can be handled by the agent."""


class FormatError(NonTerminatingException):
    """Raised when the LM's output is not in the expected format."""


class ExecutionTimeoutError(NonTerminatingException):
    """Raised when the action execution timed out."""


class TerminatingException(Exception):
    """Raised for conditions that terminate the agent."""


class Submitted(TerminatingException):
    """Raised when the LM declares that the agent has finished its task."""


class LimitsExceeded(TerminatingException):
    """Raised when the agent has reached its cost or step limit."""


class DefaultAgent:
    def __init__(self, model: Model, env: Environment, *, config_class: Callable = AgentConfig, **kwargs):
        # Extract Attack object and trace before creating config (they're not part of AgentConfig)
        self._attack = kwargs.pop("_attack", None)
        self._trace = kwargs.pop("_trace", None)
        # Extract workspace_dir (used by environment, not AgentConfig)
        self.workspace_dir = kwargs.pop("workspace_dir", None)
        # Extract defense (not part of AgentConfig)
        self._defense: Defense = kwargs.pop("_defense", None) or NoDefense()

        self.config = config_class(**kwargs)
        self.messages: list[dict] = []
        self.model = model
        self.env = env
        self.extra_template_vars = {}
        self.n_steps = 0
        self.attack_events: list[dict] = []  # Track attack injection events

    def render_template(self, template: str, **kwargs) -> str:
        template_vars = asdict(self.config) | self.env.get_template_vars() | self.model.get_template_vars()
        return Template(template, undefined=StrictUndefined).render(
            **kwargs, **template_vars, **self.extra_template_vars
        )

    def add_message(self, role: str, content: str, **kwargs):
        self.messages.append({"role": role, "content": content, **kwargs})

    def run(self, task: str, **kwargs) -> tuple[str, str]:
        """Run step() until agent is finished. Return exit status & message"""
        task = self._defense.apply_to_instruction(task)
        self.extra_template_vars |= {"task": task, **kwargs}
        self.messages = []
        self.add_message("system", self.render_template(self.config.system_template))
        self.add_message("user", self.render_template(self.config.instance_template))
        while True:
            try:
                self.step()
            except NonTerminatingException as e:
                self.add_message("user", str(e))
            except TerminatingException as e:
                self.add_message("user", str(e))
                return type(e).__name__, str(e)

    def step(self) -> dict:
        """Query the LM, execute the action, return the observation."""
        self.n_steps += 1
        return self.get_observation(self.query())

    def query(self) -> dict:
        """Query the model and return the response."""
        if 0 < self.config.step_limit <= self.model.n_calls or 0 < self.config.cost_limit <= self.model.cost:
            raise LimitsExceeded()
        response = self.model.query(self.messages)
        self.add_message("assistant", **response)
        return response

    def get_observation(self, response: dict) -> dict:
        """Execute the action and return the observation."""
        parsed_action = self.parse_action(response)
        action_str = parsed_action.get("action", "")

        # --- Defense: output gate (check before execution) ---
        if not self._defense.check_output(action_str):
            parsed_action = {**parsed_action, "action": BLOCKED_ACTION}
            action_str = BLOCKED_ACTION

        output = self.execute_action(parsed_action)
        observation = self.render_template(self.config.action_observation_template, output=output)
        
        # Attack payloads are injected at image-build time (see infuse.injection);
        # nothing is injected into observations at runtime.
        observation = self._defense.apply_to_observation(observation)

        self.add_message("user", observation)
        return output

    def parse_action(self, response: dict) -> dict:
        """Parse the action from the message. Returns the action."""
        # Try to find ```bash first (preferred format)
        actions = re.findall(r"```bash\s*\n(.*?)\n```", response["content"], re.DOTALL)
        if len(actions) == 1:
            return {"action": actions[0].strip(), **response}
        elif len(actions) > 1:
            # Multiple bash blocks - raise error
            raise FormatError(self.render_template(self.config.format_error_template, actions=actions))
        
        # Fallback: try plain triple backticks (for simpler templates)
        # Use negative lookahead to exclude ```bash (with optional whitespace)
        actions = re.findall(r"```(?!bash\s*\n)\s*\n(.*?)\n```", response["content"], re.DOTALL)
        if len(actions) == 1:
            return {"action": actions[0].strip(), **response}
        elif len(actions) > 1:
            # Multiple plain blocks - raise error
            raise FormatError(self.render_template(self.config.format_error_template, actions=actions))
        
        # If neither pattern matches, raise format error
        # Count all code blocks for error message
        all_code_blocks = re.findall(r"```(?:bash)?\s*\n(.*?)\n```", response["content"], re.DOTALL)
        raise FormatError(self.render_template(self.config.format_error_template, actions=all_code_blocks))

    def execute_action(self, action: dict) -> dict:
        try:
            output = self.env.execute(action["action"])
        except subprocess.TimeoutExpired as e:
            output = e.output.decode("utf-8", errors="replace") if e.output else ""
            raise ExecutionTimeoutError(
                self.render_template(self.config.timeout_template, action=action, output=output)
            )
        except TimeoutError:
            raise ExecutionTimeoutError(self.render_template(self.config.timeout_template, action=action, output=""))
        self.has_finished(output)
        return output

    def has_finished(self, output: dict[str, str]):
        """Raises Submitted exception with final output if the agent has finished its task."""
        lines = output.get("output", "").lstrip().splitlines(keepends=True)
        if lines:
            first_line = lines[0].strip()
            # Check for completion signals
            if first_line in ["MINI_SWE_AGENT_FINAL_OUTPUT", "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"]:
                raise Submitted("".join(lines[1:]))
            # Check for task failure signal - treat as signal to stop
            if first_line.startswith("TASK_FAILED"):
                raise Submitted(first_line)