# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import numpy as np
import torch.nn as nn
from torch.optim import Adam, RMSprop

from maro.rl import (
    AbsAgent, ActorCritic, ActorCriticConfig, FullyConnectedBlock, LearningModel, LearningModule, OptimizerOptions,
    PolicyGradient, PolicyGradientConfig, PPO, PPOConfig, SimpleAgentManager
)
from maro.utils import set_seeds


class POAgent(AbsAgent):
    def train(self, states: np.ndarray, actions: np.ndarray, rewards: np.ndarray):
        self._algorithm.train(states, actions, rewards)


def create_po_agents(agent_id_list, config):
    algorithm_map = {
        "actor_critic": (ActorCritic, ActorCriticConfig),
        "ppo": (PPO, PPOConfig),
        "policy_gradient": (PolicyGradient, PolicyGradientConfig)
    }
    input_dim, num_actions = config.input_dim, config.num_actions
    set_seeds(config.seed)
    config = config[config.algorithm]
    algorithm_cls, algorithm_config = algorithm_map[config.algorithm]
    agent_dict = {}
    for agent_id in agent_id_list:
        actor_module = LearningModule(
            "actor",
            [FullyConnectedBlock(
                input_dim=input_dim,
                output_dim=num_actions,
                activation=nn.Tanh,
                is_head=True,
                **config.actor_model
            )],
            optimizer_options=OptimizerOptions(cls=Adam, params=config.actor_optimizer)
        )

        if config.algorithm in {"actor_critic", "ppo"}:
            critic_module = LearningModule(
                "critic",
                [FullyConnectedBlock(
                    input_dim=config.input_dim,
                    output_dim=1,
                    activation=nn.LeakyReLU,
                    is_head=True,
                    **config.critic_model
                )],
                optimizer_options=OptimizerOptions(cls=RMSprop, params=config.critic_optimizer)
            )

            algorithm = algorithm_cls(
                LearningModel(actor_module, critic_module),
                algorithm_config(critic_loss_func=nn.functional.smooth_l1_loss, **config.config)
            )
        else:
            algorithm = algorithm_cls(LearningModel(actor_module), algorithm_config(**config.config))

        agent_dict[agent_id] = POAgent(name=agent_id, algorithm=algorithm)

    return agent_dict


class POAgentManager(SimpleAgentManager):
    def train(self, experiences_by_agent: dict):
        for agent_id, exp in experiences_by_agent.items():
            if isinstance(exp, list):
                for trajectory in exp:
                    self.agent_dict[agent_id].train(trajectory["states"], trajectory["actions"], trajectory["rewards"])
            else:
                self.agent_dict[agent_id].train(exp["states"], exp["actions"], exp["rewards"])
