"""Main entry point for the Multi-Agent Procurement System."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import time

from agents.Agent0 import MasterOrchestrator

def main():
    """Run the interactive procurement assistant."""
    print("="*50)
    print("Procurement Assistant")
    print("="*50)
    print("\nType 'exit' to quit")
    
    orchestrator = MasterOrchestrator()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\nGoodbye!")
                break
            
            response = orchestrator.process_request(user_input)
            time.sleep(1)
            print(f"\nAssistant: {response}")
            
        except KeyboardInterrupt:
            time.sleep(1)
            print("\n\nGoodbye! Have a nice day!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
