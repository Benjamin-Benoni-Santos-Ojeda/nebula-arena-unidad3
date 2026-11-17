"""Benchmark reproducible de la práctica 3.1."""

import argparse
import json
import math
import platform
from pathlib import Path
from time import perf_counter

import gymnasium as gym
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("PyTorch no detecta una GPU CUDA")

    torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=True)
    with gym.make("CartPole-v1") as env:
        model = PPO("MlpPolicy", env, seed=args.seed, device=args.device)
        start = perf_counter()
        model.learn(total_timesteps=100_000)
        if args.device == "cuda":
            torch.cuda.synchronize()
        train_seconds = perf_counter() - start
        model_path = args.output / f"bot-{args.device}"
        model.save(model_path)
        cpu_model = PPO.load(model_path, device="cpu")
        observation, _ = env.reset(seed=args.seed + 1)
        for _ in range(100):
            cpu_model.predict(observation, deterministic=True)
        start = perf_counter()
        for _ in range(10_000):
            cpu_model.predict(observation, deterministic=True)
        seconds = perf_counter() - start

    with gym.make("CartPole-v1") as evaluation_env:
        evaluation_env.reset(seed=args.seed + 2)
        mean, deviation = evaluate_policy(
            cpu_model, evaluation_env, n_eval_episodes=20, warn=False
        )
    result = {
        "training_device": args.device,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "torch": torch.__version__,
        "seed": args.seed,
        "actual_timesteps": model.num_timesteps,
        "training_seconds": train_seconds,
        "cpu_inference_mean_ms": seconds / 10,
        "decisions_per_second_single_thread": 10_000 / seconds,
        "minimum_vcpu_2000_bots_at_10hz": math.ceil(2 * seconds),
        "mean_reward_20_episodes": mean,
        "reward_stddev": deviation,
    }
    (args.output / f"ppo-{args.device}.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
