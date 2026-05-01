# src/simulation/ppo_agent.py
import tensorflow as tf
from tensorflow.keras import layers, optimizers
import numpy as np

class PPOAgent:
    def __init__(self, state_dim, num_nodes, learning_rate=0.001):
        self.num_nodes = num_nodes
        
        # Build Actor Network (Outputs CH probabilities)
        actor_input = layers.Input(shape=(state_dim,))
        x = layers.Dense(128, activation='relu')(actor_input)
        x = layers.Dense(64, activation='relu')(x)
        # Softmax ensures probabilities sum to 1
        actor_output = layers.Dense(num_nodes, activation='softmax')(x)
        self.actor = tf.keras.Model(inputs=actor_input, outputs=actor_output)
        self.actor_opt = optimizers.Adam(learning_rate=learning_rate)

        # Build Critic Network (Outputs expected network lifespan / Value)
        critic_input = layers.Input(shape=(state_dim,))
        y = layers.Dense(128, activation='relu')(critic_input)
        y = layers.Dense(64, activation='relu')(y)
        critic_output = layers.Dense(1, activation='linear')(y)
        self.critic = tf.keras.Model(inputs=critic_input, outputs=critic_output)
        self.critic_opt = optimizers.Adam(learning_rate=learning_rate)

    def get_action_probs(self, state):
        """Predicts the probability distribution for CH election."""
        state = np.expand_dims(state, axis=0) # Add batch dimension
        probs = self.actor(state, training=False)
        return probs.numpy()[0]

    def train_step(self, state, target_value, advantage):
        """
        Simplified training step for the Actor-Critic networks.
        In a full PPO implementation, this would include clipped surrogate objective.
        """
        state = np.expand_dims(state, axis=0)
        target_value = np.array([[target_value]])
        advantage = np.array([[advantage]])

        # Train Critic
        with tf.GradientTape() as tape:
            v_pred = self.critic(state, training=True)
            critic_loss = tf.keras.losses.MSE(target_value, v_pred)
        critic_grads = tape.gradient(critic_loss, self.critic.trainable_variables)
        self.critic_opt.apply_gradients(zip(critic_grads, self.critic.trainable_variables))

        # Train Actor
        with tf.GradientTape() as tape:
            probs = self.actor(state, training=True)
            # Simplified policy gradient loss: -log(prob) * advantage
            log_probs = tf.math.log(probs + 1e-10) 
            actor_loss = -tf.reduce_mean(log_probs * advantage)
        actor_grads = tape.gradient(actor_loss, self.actor.trainable_variables)
        self.actor_opt.apply_gradients(zip(actor_grads, self.actor.trainable_variables))
        
        return critic_loss.numpy(), actor_loss.numpy()
