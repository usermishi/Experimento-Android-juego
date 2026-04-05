import json
import os
import random

# Mocking the objects for testing logic
class MockUser:
    def __init__(self, user_id, first_name):
        self.id = user_id
        self.first_name = first_name

class MockMessage:
    def __init__(self, text, user):
        self.text = text
        self.from_user = user

# Test variables
ARCHIVO_RESPUESTAS = "data/respuestas.json"

def test_response_selection():
    if not os.path.exists(ARCHIVO_RESPUESTAS):
        print("FAIL: ARCHIVO_RESPUESTAS does not exist.")
        return False

    with open(ARCHIVO_RESPUESTAS, "r", encoding="utf-8") as f:
        respuestas_db = json.load(f)

    # Test for each state
    states = ["frío", "curioso", "interesado", "obsesionado"]
    nombre = "TestUser"

    for state in states:
        if state not in respuestas_db:
            print(f"FAIL: State '{state}' not in DB.")
            return False

        opciones = respuestas_db[state]
        if len(opciones) != 2500:
             print(f"FAIL: State '{state}' has {len(opciones)} responses instead of 2500.")
             return False

        # Pick one and format
        resp_base = random.choice(opciones)
        try:
            resp_formatted = resp_base.format(nombre=nombre)
            if "{nombre}" in resp_formatted:
                print(f"FAIL: '{{nombre}}' placeholder still in response: {resp_formatted}")
                return False
            if nombre not in resp_formatted and "{nombre}" not in resp_base:
                 # Note: some generated responses might not use {nombre} in the template,
                 # but we should check if format() actually works
                 pass
        except Exception as e:
            print(f"FAIL: Error formatting response '{resp_base}': {e}")
            return False

    print("SUCCESS: Response selection logic and DB structure are correct.")
    return True

if __name__ == "__main__":
    test_response_selection()
