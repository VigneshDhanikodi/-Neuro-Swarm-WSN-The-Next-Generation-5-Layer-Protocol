# src/simulation/network_env.py
import numpy as np

class WSNEnvironment:
    def __init__(self, num_nodes=100, area_size=500):
        self.num_nodes = num_nodes
        self.area_size = area_size
        self.uav_pos = np.array([area_size/2, area_size/2])
        self.reset()
        
        # Energy parameters (Joules)
        self.INITIAL_ENERGY = 100.0
        self.E_ELEC = 50e-9       # 50 nJ/bit
        self.E_FS = 10e-12        # 10 pJ/bit/m^2 (Free space)
        self.E_MP = 0.0013e-12    # 0.0013 pJ/bit/m^4 (Multipath)
        self.THRESHOLD_DIST = 87.0
        self.PACKET_SIZE = 4000   # bits

    def reset(self):
        """Initializes the network topology and energy levels."""
        self.node_positions = np.random.rand(self.num_nodes, 2) * self.area_size
        self.node_energy = np.full(self.num_nodes, 100.0)
        self.alive_nodes = np.ones(self.num_nodes, dtype=bool)
        self.uav_pos = np.array([self.area_size/2, self.area_size/2])
        return self._get_state()

    def _get_state(self):
        """Returns the current state vector for the RL Agent."""
        dist_to_uav = np.linalg.norm(self.node_positions - self.uav_pos, axis=1)
        # Normalize states
        norm_energy = self.node_energy / 100.0
        norm_dist = dist_to_uav / (self.area_size * np.sqrt(2))
        
        # Stack into a single state vector: [energy, distance, alive_status]
        state = np.column_stack((norm_energy, norm_dist, self.alive_nodes.astype(float)))
        return state.flatten()

    def calculate_energy_cost(self, distance):
        """Calculates energy required to transmit a packet over 'distance'."""
        if distance < self.THRESHOLD_DIST:
            cost = self.PACKET_SIZE * (self.E_ELEC + self.E_FS * (distance ** 2))
        else:
            cost = self.PACKET_SIZE * (self.E_ELEC + self.E_MP * (distance ** 4))
        return cost

    def step(self, action_probs):
        """
        Executes one epoch based on the AI's Cluster Head selection.
        action_probs: Array of probabilities output by the PPO Actor network.
        """
        # 1. Elect Cluster Heads based on AI probabilities (Top 10%)
        num_chs = max(1, int(self.num_nodes * 0.10))
        # Mask out dead nodes
        action_probs = action_probs * self.alive_nodes
        if np.sum(action_probs) == 0:
             return self._get_state(), 0, True, {} # All nodes dead
             
        action_probs /= np.sum(action_probs) 
        ch_indices = np.random.choice(self.num_nodes, num_chs, p=action_probs, replace=False)
        
        # 2. UAV Path Planning (Simplified: Move to centroid of CHs)
        ch_positions = self.node_positions[ch_indices]
        self.uav_pos = np.mean(ch_positions, axis=0)

        # 3. Calculate Energy Consumption for this epoch
        epoch_energy_cost = 0
        for i in range(self.num_nodes):
            if not self.alive_nodes[i]: continue
            
            if i in ch_indices:
                # CH transmitting directly to overhead UAV (very short distance)
                dist_to_uav = np.linalg.norm(self.node_positions[i] - self.uav_pos)
                cost = self.calculate_energy_cost(dist_to_uav)
            else:
                # Member node transmitting to nearest CH
                distances_to_chs = np.linalg.norm(ch_positions - self.node_positions[i], axis=1)
                min_dist = np.min(distances_to_chs)
                cost = self.calculate_energy_cost(min_dist)
            
            self.node_energy[i] -= cost
            epoch_energy_cost += cost
            
            # Check for node death
            if self.node_energy[i] <= 0:
                self.node_energy[i] = 0
                self.alive_nodes[i] = False

        # 4. Calculate Reward
        # Reward = number of alive nodes - penalty for energy variance
        total_alive = np.sum(self.alive_nodes)
        energy_variance = np.var(self.node_energy[self.alive_nodes]) if total_alive > 0 else 0
        reward = total_alive - (energy_variance * 0.1)

        # 5. Check Termination
        done = total_alive == 0

        info = {
            'alive_nodes': total_alive,
            'avg_energy': np.mean(self.node_energy[self.alive_nodes]) if total_alive > 0 else 0,
            'total_cost': epoch_energy_cost
        }

        return self._get_state(), reward, done, info
