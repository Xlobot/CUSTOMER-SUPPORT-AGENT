"""
training/train.py — NetCare AI
High-Efficiency SFT Training Pipeline for Qwen2.5-3B-Instruct using Unsloth (FastLanguageModel) & QLoRA.
Unsloth provides:
- 2x faster training speed
- 70% lower VRAM consumption (enables fine-tuning on 6GB-8GB GPUs and free Google Colab T4)
- Native 4-bit NF4 quantized base loading with flash-attention optimization
"""

import os
import json
import sys

def generate_unsloth_training_notebook():
    """Generates a self-contained, optimized Unsloth fine-tuning notebook for Qwen2.5-3B-Instruct."""
    notebook_content = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {"provenance": []},
            "language_info": {"name": "python"},
            "accelerator": "GPU"
        },
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# NetCare AI — Qwen2.5-3B-Instruct Fine-Tuning with Unsloth\n",
                    "This notebook fine-tunes **Qwen2.5-3B-Instruct** on the NetCare AI 5-agent multi-task dataset using **Unsloth (FastLanguageModel)** and QLoRA 4-bit.\n",
                    "- **Speed:** 2x faster than standard HuggingFace PEFT\n",
                    "- **Memory:** 70% less VRAM (runs smoothly on Google Colab free T4 GPU)"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 1. Install Unsloth and modern dependencies\n",
                    "!pip install --no-deps \"xformers<0.0.29\" \"trl<0.9.0\" peft accelerate bitsandbytes\n",
                    "!pip install \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\""
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 2. Load Qwen2.5-3B-Instruct in 4-bit with Unsloth\n",
                    "from unsloth import FastLanguageModel\n",
                    "import torch\n\n",
                    "max_seq_length = 2048\n",
                    "dtype = None  # None for auto detection (Float16 or Bfloat16)\n",
                    "load_in_4bit = True\n\n",
                    "model, tokenizer = FastLanguageModel.from_pretrained(\n",
                    "    model_name=\"Qwen/Qwen2.5-3B-Instruct\",\n",
                    "    max_seq_length=max_seq_length,\n",
                    "    dtype=dtype,\n",
                    "    load_in_4bit=load_in_4bit,\n",
                    ")\n\n",
                    "# 3. Add LoRA adapters targeting all attention and MLP projection layers\n",
                    "model = FastLanguageModel.get_peft_model(\n",
                    "    model,\n",
                    "    r=16,\n",
                    "    target_modules=[\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",\n",
                    "                    \"gate_proj\", \"up_proj\", \"down_proj\"],\n",
                    "    lora_alpha=32,\n",
                    "    lora_dropout=0,  # Optimized to 0 for Unsloth fast kernels\n",
                    "    bias=\"none\",\n",
                    "    use_gradient_checkpointing=\"unsloth\",  # Very low VRAM usage\n",
                    "    random_state=42,\n",
                    "    use_rslora=False,\n",
                    "    loftq_config=None,\n",
                    ")\n",
                    "print(\"Unsloth FastLanguageModel initialized with LoRA adapters.\")"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 4. Format Dataset with NetCare Multi-Agent Prompt Template\n",
                    "from datasets import load_dataset\n\n",
                    "# Load processed train.jsonl from NetCare dataset\n",
                    "# Upload datasets/processed/train.jsonl to Colab workspace\n",
                    "dataset = load_dataset(\"json\", data_files={\"train\": \"train.jsonl\"}, split=\"train\")\n\n",
                    "def format_prompts(batch):\n",
                    "    texts = []\n",
                    "    for system, user, assistant in zip(batch[\"system\"], batch[\"user\"], batch[\"assistant\"]):\n",
                    "        prompt = f\"<|im_start|>system\\n{system}<|im_end|>\\n<|im_start|>user\\n{user}<|im_end|>\\n<|im_start|>assistant\\n{assistant}<|im_end|>\"\n",
                    "        texts.append(prompt)\n",
                    "    return {\"text\": texts}\n\n",
                    "formatted_dataset = dataset.map(format_prompts, batched=True)\n",
                    "print(f\"Loaded and formatted {len(formatted_dataset)} multi-agent training samples.\")"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 5. Train with SFTTrainer\n",
                    "from trl import SFTTrainer\n",
                    "from transformers import TrainingArguments\n\n",
                    "trainer = SFTTrainer(\n",
                    "    model=model,\n",
                    "    tokenizer=tokenizer,\n",
                    "    train_dataset=formatted_dataset,\n",
                    "    dataset_text_field=\"text\",\n",
                    "    max_seq_length=max_seq_length,\n",
                    "    dataset_num_proc=2,\n",
                    "    packing=False,\n",
                    "    args=TrainingArguments(\n",
                    "        per_device_train_batch_size=2,\n",
                    "        gradient_accumulation_steps=4,\n",
                    "        warmup_steps=10,\n",
                    "        max_steps=120,\n",
                    "        learning_rate=2e-4,\n",
                    "        fp16=not torch.cuda.is_bf16_supported(),\n",
                    "        bf16=torch.cuda.is_bf16_supported(),\n",
                    "        logging_steps=10,\n",
                    "        optim=\"adamw_8bit\",\n",
                    "        weight_decay=0.01,\n",
                    "        lr_scheduler_type=\"cosine\",\n",
                    "        seed=42,\n",
                    "        output_dir=\"./unsloth_netcare_checkpoints\",\n",
                    "    ),\n",
                    ")\n\n",
                    "trainer_stats = trainer.train()\n",
                    "print(\"Training complete! Train runtime:\", trainer_stats.metrics.get(\"train_runtime\"))"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 6. Save LoRA weights and GGUF export for local deployment\n",
                    "model.save_pretrained(\"netcare_qwen_unsloth_lora\")\n",
                    "tokenizer.save_pretrained(\"netcare_qwen_unsloth_lora\")\n\n",
                    "# Export to 4-bit GGUF for instant local CPU/GPU execution\n",
                    "model.save_pretrained_gguf(\"netcare_qwen_gguf\", tokenizer, quantization_method=\"q4_k_m\")\n",
                    "print(\"Model saved and exported to GGUF format for local deployment.\")"
                ]
            }
        ]
    }

    colab_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "training", "train_colab.ipynb")
    with open(colab_path, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2)
    print(f"[UNSLOTH] Generated Unsloth fine-tuning pipeline notebook: {colab_path}")

if __name__ == "__main__":
    generate_unsloth_training_notebook()
