#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
from pathlib import Path

from definitions import DATA_DIR, OUTPUT_DIR, LOGS_DIR


class PathUtil:
    @staticmethod
    def orig_data_dir():
        path = Path(DATA_DIR) / 'orig_data'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def orig_data(filename: str, ext: str):
        path = Path(DATA_DIR) / 'orig_data'
        path.mkdir(parents=True, exist_ok=True)
        path = path / f'{filename}.{ext}'
        return str(path)

    @staticmethod
    def processed_data_dir():
        path = Path(DATA_DIR) / 'processed_data'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def processed_data(filename: str, ext: str):
        path = Path(DATA_DIR) / 'processed_data'
        path.mkdir(parents=True, exist_ok=True)
        path = path / f'{filename}.{ext}'
        return str(path)

    @staticmethod
    def fina_data_dir():
        path = Path(DATA_DIR) / 'final_data'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def Juliet_dir():
        path = Path(DATA_DIR) / 'Juliet'
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def final_data(filename: str, ext: str):
        path = Path(DATA_DIR) / 'final_data'
        path.mkdir(parents=True, exist_ok=True)
        path = path / f'{filename}.{ext}'
        return str(path)

    @staticmethod
    def resource_data(filename: str, ext: str):
        path = Path(DATA_DIR) / 'resource'
        path.mkdir(parents=True, exist_ok=True)
        path = path / f'{filename}.{ext}'
        return str(path)

    @staticmethod
    def output_data(filename: str, ext: str):
        path = Path(OUTPUT_DIR)
        path.mkdir(parents=True, exist_ok=True)
        path = path / f'{filename}.{ext}'
        return str(path)

    @staticmethod
    def call_chain_data(filename: str, ext: str):
        path = Path(DATA_DIR) / 'call_chain'
        path.mkdir(parents=True, exist_ok=True)
        path = path / f'{filename}.{ext}'
        return str(path)

    @staticmethod
    def UFA_result_data(filename: str, ext: str):
        path = Path(DATA_DIR) / 'SA_results' / 'final_dataset' / 'UAF'
        path.mkdir(parents=True, exist_ok=True)
        path = path / f'{filename}.{ext}'
        return str(path)


    @staticmethod
    def exists(path):
        return os.path.exists(path)


    @staticmethod
    def check_file_exists(path):
        return os.path.exists(path)
