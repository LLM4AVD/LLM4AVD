import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
DATA_DIR = str(Path(ROOT_DIR) / "data")  # This is the data of this project
OUTPUT_DIR = str(Path(ROOT_DIR) / "output")  # This is the output of this project
LOGS_DIR = str(Path(ROOT_DIR) / "log")  # This is the log of this project
MODEL_DIR = str(Path(ROOT_DIR) / "model")
KNOWLEDGE_EXTRACTION_DIR = str(Path(ROOT_DIR) / "vul_knowledge_extraction")
