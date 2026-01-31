import json
import os
from .generic import GenericParser

PARSER_REGISTRY = {}
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'banks_config.json')

def register_parser(bank_code):
    """Decorator to register a bank parser class"""
    def decorator(cls):
        PARSER_REGISTRY[bank_code] = cls
        return cls
    return decorator

def get_parser(bank_code):
    """Factory function to get a parser instance"""
    
    # 1. Check Registry (Custom Python Implementations)
    if bank_code in PARSER_REGISTRY:
        return PARSER_REGISTRY[bank_code]()

    # 2. Check Configuration (Generic Parser)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if bank_code in config:
                    return GenericParser(config[bank_code])
        except Exception as e:
            print(f"Failed to load bank config: {e}")

    # 3. Fallback (Default to Post Office if available in registry)
    if '700' in PARSER_REGISTRY:
        return PARSER_REGISTRY['700']()
        
    raise ValueError(f"No parser found for bank code: {bank_code}")
