import sys
try:
    with open('agent_log.txt', 'r', encoding='utf-8') as f:
        print(f.read())
except Exception as e:
    with open('agent_log.txt', 'r', encoding='latin-1') as f:
        print(f.read())
