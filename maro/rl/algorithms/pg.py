# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import numpy as np
import torch
import torch.nn as nn

from maro.rl.algorithms.abs_algorithm import AbsAlgorithm


class PolicyGradientConfig:
    """Configuration for the Policy Gradient (PG) algorithm.

    Args:
        num_actions (int): number of possible actions
        reward_decay (float): reward decay as defined in standard RL terminology
    """
    __slots__ = ["num_actions", "reward_decay"]

    def __init__(self, num_actions: int, reward_decay: float):
        self.num_actions = num_actions
        self.reward_decay = reward_decay


class PolicyGradient(AbsAlgorithm):
    """Policy Gradient algorithm.

    The Policy Gradient algorithm base on the policy gradient theorem, a.k.a. REINFORCE.

    Args:
        policy_model (nn.Module): model for generating actions given states.
        optimizer_cls: torch optimizer class for the policy model. If this is None, the policy model is not trainable.
        optimizer_params: parameters required for the policy optimizer class.
        hyper_params: hyper-parameter set for the AC algorithm.
    """

    def __init__(
        self, policy_model: nn.Module, optimizer_cls, optimizer_params,
        hyper_params: PolicyGradientConfig
    ):
        super().__init__()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._policy_model = policy_model.to(self._device)
        if optimizer_cls is not None:
            self._optimizer = optimizer_cls(self._policy_model.parameters(), **optimizer_params)
        self._hyper_params = hyper_params

    @property
    def model(self):
        return self._policy_model

    def choose_action(self, state: np.ndarray, epsilon: float = None):
        state = torch.from_numpy(state).unsqueeze(0).to(self._device)   # (1, state_dim)
        self._policy_model.eval()
        with torch.no_grad():
            action_dist = self._policy_model(state).squeeze().numpy()  # (num_actions,)
        return np.random.choice(self._hyper_params.num_actions, p=action_dist)

    def train(self, states: np.ndarray, actions: np.ndarray, returns: np.ndarray):
        if hasattr(self, "_optimizer"):
            states = torch.from_numpy(states).to(self._device)   # (N, state_dim)
            actions = torch.from_numpy(actions).to(self._device)  # (N,)
            returns = torch.from_numpy(returns).to(self._device)
            action_prob = self._policy_model(states).gather(1, actions.unsqueeze(1)).squeeze()   # (N, 1)
            policy_loss = -(torch.log(action_prob) * returns).mean()
            self._optimizer.zero_grad()
            policy_loss.backward()
            self._optimizer.step()