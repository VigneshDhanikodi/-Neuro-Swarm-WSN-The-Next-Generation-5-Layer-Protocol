# src/simulation/advanced_drl_uav_sim.py
import argparse
from network_env import WSNEnvironment
from ppo_agent import PPOAgent

def run_simulation(epochs=5000):
    print("Initializing Neuro-Swarm WSN Simulation...")
    
    NUM_NODES = 100
    env = WSNEnvironment(num_nodes=NUM_NODES, area_size=500)
    
    # State dimension: (energy, distance, alive_status) per node
    state_dim = NUM_NODES * 3 
    agent = PPOAgent(state_dim=state_dim, num_nodes=NUM_NODES)
    
    state = env.reset()
    
    metrics = {
        'fnd': None,  # First Node Dies
        'hnd': None,  # Half Nodes Die
        'history': []
    }

    print(f"Starting {epochs} epochs...")
    
    for epoch in range(1, epochs + 1):
        # 1. AI predicts CH probabilities
        action_probs = agent.get_action_probs(state)
        
        # 2. Environment steps forward based on AI's choice
        next_state, reward, done, info = env.step(action_probs)
        
        # 3. Record Metrics
        alive = info['alive_nodes']
        if metrics['fnd'] is None and alive < NUM_NODES:
            metrics['fnd'] = epoch
            print(f">>> FIRST NODE DIED (FND) at Epoch {epoch}")
            
        if metrics['hnd'] is None and alive <= NUM_NODES / 2:
            metrics['hnd'] = epoch
            print(f">>> HALF NODES DIED (HND) at Epoch {epoch}")

        metrics['history'].append(info)
        
        # 4. Simplified Training Step (Online learning)
        # Estimate Value of next state
        next_v = agent.critic(next_state.reshape(1, -1)).numpy()[0][0]
        current_v = agent.critic(state.reshape(1, -1)).numpy()[0][0]
        
        # Calculate Advantage (Reward + Discounted Next Value - Current Value)
        advantage = reward + (0.99 * next_v) - current_v
        target_value = reward + (0.99 * next_v)
        
        c_loss, a_loss = agent.train_step(state, target_value, advantage)
        
        state = next_state
        
        if epoch % 500 == 0 or done:
            print(f"Epoch {epoch:4d} | Alive: {alive:3d} | Avg Energy: {info['avg_energy']:.2f}J | Reward: {reward:.2f}")
            
        if done:
            print("Network depleted. Simulation complete.")
            break

    print("\n--- SIMULATION RESULTS ---")
    print(f"First Node Dies (FND): {metrics['fnd']}")
    print(f"Half Nodes Die (HND):  {metrics['hnd']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Neuro-Swarm Simulation')
    parser.add_argument('--epochs', type=int, default=5000, help='Number of epochs to simulate')
    args = parser.parse_args()
    
    run_simulation(epochs=args.epochs)
