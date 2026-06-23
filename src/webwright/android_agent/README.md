# Webwright Android M3A

This package contains the M3A (Multimodal Autonomous Agent for Android) agent
used by Webwright's `local_android_m3a` environment.

## Modules

- `m3a.py`: M3A step loop, prompts, and SoM action selection
- `base_agent.py`: `EnvironmentInteractingAgent` base class
- `transition_guard.py`: UI transition facts and stuck-loop guards

Shared Android types and utilities live in `webwright.android`.

## Usage

M3A is wired through `webwright.agents.m3a_android.M3aAndroidAgent` and
`webwright.environments.local_android_m3a.LocalAndroidM3aEnvironment`.
